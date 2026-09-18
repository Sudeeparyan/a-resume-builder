"""
The scan pipeline.

Orchestrator-worker with phase gates and a final supervisor -- the shape that
survived production use. No free-form agent collaboration.

    preflight -> source -> normalize -> hard_filter
              -> [GATE] sponsorship -> [GATE] tracker -> [GATE] link_verify
              -> jd_parse -> company_intel -> skill_predict
              -> fit_score -> rank -> persist

Each phase records its duration (which is what makes the ETA honest) and
checkpoints its output, so a run stopped by a usage limit resumes at the failed
phase instead of paying for the whole thing twice.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime
from typing import Any

from .. import db, legacy, settings
from ..agents import deterministic as D
from ..llm import registry
from ..llm.provider import ProviderUnavailable, QuotaExhausted
from ..models import (
    ExcludedJob, JobPosting, LinkStatus, RunStatus, ScoredJob, StageState,
    StageStatus, Tier,
)
from ..services import context_loader, scoring, workspace_sync
from ..services.sources import ats as ats_sources
from ..services.sources import feeds as feed_sources
from ..services.sources.base import gather_sources
from . import eta, events


PHASES: list[tuple[str, str, bool]] = [
    ("preflight", "Getting your facts and checking what to skip", False),
    ("source", "Looking for openings", False),
    ("normalize", "Removing duplicates", False),
    ("hard_filter", "Dropping roles above your level", False),
    ("sponsorship", "Checking which ones rule out sponsorship", False),
    ("tracker", "Removing anywhere you have already applied", False),
    ("link_verify", "Checking every apply link still works", False),
    ("jd_parse", "Reading what each job actually asks for", True),
    ("company_intel", "Researching each company", True),
    ("skill_predict", "Working out your odds", True),
    ("fit_score", "Scoring and ranking", False),
    ("persist", "Writing your summary page", False),
]


class Run:
    """One scan. Owns its state, its events and its checkpoints."""

    def __init__(self, params: dict[str, Any] | None = None, run_id: str | None = None):
        self.id = run_id or uuid.uuid4().hex[:12]
        self.params = params or {}
        self.status = RunStatus.QUEUED
        self.stages: dict[str, StageState] = {
            key: StageState(key=key, label=label) for key, label, _llm in PHASES
        }
        self.started_at: datetime | None = None
        self.finished_at: datetime | None = None
        self.error: str | None = None
        self.message = ""
        self.cost_usd = 0.0
        self.resume_after: datetime | None = None

        self.postings: list[JobPosting] = []
        self.scored: list[ScoredJob] = []
        self.excluded: list[ExcludedJob] = []
        self.source_report: list[dict[str, Any]] = []
        self.counts: dict[str, int] = {}

    # -- plumbing ---------------------------------------------------------
    def plan(self) -> list[eta.PhasePlan]:
        n = max(1, len(self.postings) or self.params.get("count", 10))
        sizes = {
            "source": 6, "normalize": n, "hard_filter": n, "sponsorship": n,
            "tracker": n, "link_verify": min(n, 25), "jd_parse": min(n, 15),
            "company_intel": min(n, 8), "skill_predict": min(n, 8), "fit_score": n,
        }
        return [
            eta.PhasePlan(key=k, label=lbl, items=sizes.get(k, 1), llm=llm)
            for k, lbl, llm in PHASES
        ]

    def done_keys(self) -> set[str]:
        return {k for k, s in self.stages.items() if s.status in (StageStatus.DONE, StageStatus.SKIPPED)}

    async def _eta(self) -> None:
        est = eta.estimate(self.plan(), self.done_keys())
        await events.emit(self.id, "eta", message=est["human"], **est)

    async def _start(self, key: str, items: int = 0) -> float:
        st = self.stages[key]
        st.status = StageStatus.RUNNING
        st.items_total = items
        st.started_at = datetime.now()
        await events.emit(self.id, "stage_started", stage=key, message=st.label, items=items)
        await self._eta()
        return time.perf_counter()

    async def _finish(self, key: str, t0: float, note: str = "", items: int = 0) -> None:
        st = self.stages[key]
        st.status = StageStatus.DONE
        st.finished_at = datetime.now()
        st.duration_ms = int((time.perf_counter() - t0) * 1000)
        st.items_done = items or st.items_total
        st.note = note
        eta.record(key, st.duration_ms, max(1, st.items_done))
        await events.emit(
            self.id, "stage_finished", stage=key, message=note,
            duration_ms=st.duration_ms, items=st.items_done,
        )
        self._save()

    async def _skip(self, key: str, why: str) -> None:
        st = self.stages[key]
        st.status = StageStatus.SKIPPED
        st.note = why
        await events.emit(self.id, "stage_finished", stage=key, message=why, skipped=True)

    async def _log(self, msg: str, stage: str | None = None, **data: Any) -> None:
        await events.emit(self.id, "log", stage=stage, message=msg, **data)

    def _exclude(self, items: list[ExcludedJob]) -> None:
        self.excluded.extend(items)
        for e in items:
            db.connect().execute(
                "INSERT INTO excluded (run_id, company, role_title, url, stage, why,"
                " triggering_sentence, at) VALUES (?,?,?,?,?,?,?,?)",
                (self.id, e.company, e.role_title, e.url, e.stage, e.why,
                 e.triggering_sentence, db.now()),
            )

    def _save(self) -> None:
        db.connect().execute(
            "INSERT INTO runs (id, kind, status, params, stages, message, error,"
            " cost_usd, started_at, finished_at, resume_after, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(id) DO UPDATE SET status=excluded.status,"
            " stages=excluded.stages, message=excluded.message, error=excluded.error,"
            " cost_usd=excluded.cost_usd, finished_at=excluded.finished_at,"
            " resume_after=excluded.resume_after",
            (self.id, "scan", self.status.value, db.dumps(self.params),
             db.dumps([s.model_dump(mode="json") for s in self.stages.values()]),
             self.message, self.error, self.cost_usd,
             self.started_at.isoformat() if self.started_at else None,
             self.finished_at.isoformat() if self.finished_at else None,
             self.resume_after.isoformat() if self.resume_after else None,
             db.now()),
        )

    def state(self) -> dict[str, Any]:
        elapsed = int((datetime.now() - self.started_at).total_seconds()) if self.started_at else 0
        est = eta.estimate(self.plan(), self.done_keys())
        return {
            "id": self.id, "kind": "scan", "status": self.status.value,
            "params": self.params, "message": self.message, "error": self.error,
            "stages": [s.model_dump(mode="json") for s in self.stages.values()],
            "elapsed_seconds": elapsed,
            "eta_seconds_p50": est["p50_seconds"], "eta_seconds_p80": est["p80_seconds"],
            "eta_human": est["human"],
            "cost_usd": round(self.cost_usd, 4),
            "counts": self.counts,
            "source_report": self.source_report,
            "resume_after": self.resume_after.isoformat() if self.resume_after else None,
        }

    # -- the pipeline -----------------------------------------------------
    async def execute(self) -> None:
        self.status = RunStatus.RUNNING
        self.started_at = datetime.now()
        self._save()
        events.restore_seq(self.id)
        await events.emit(
            self.id, "run_started", message="Starting your job search",
            plan=[{"key": k, "label": l} for k, l, _ in PHASES],
        )
        try:
            await self._run_phases()
            self.status = RunStatus.DONE
            self.message = self._closing_note()
        except QuotaExhausted as exc:
            self.status = RunStatus.WAITING_QUOTA
            self.resume_after = exc.resume_at(settings.get_settings().quota_retry_minutes)
            self.message = (
                "Paused — the AI usage limit was reached. Everything found so far is "
                f"saved. This will pick up again after {self.resume_after:%H:%M}."
            )
            await events.emit(self.id, "quota_wait", message=self.message,
                              resume_after=self.resume_after.isoformat())
        except Exception as exc:  # noqa: BLE001
            self.status = RunStatus.FAILED
            self.error = f"{type(exc).__name__}: {exc}"
            self.message = "Something went wrong. Nothing was lost — see the details below."
            await events.emit(self.id, "error", message=self.message, detail=self.error)
        finally:
            self.finished_at = datetime.now()
            self._save()
            await events.emit(
                self.id, "run_finished", message=self.message,
                status=self.status.value, counts=self.counts,
                duration_s=int((self.finished_at - (self.started_at or self.finished_at)).total_seconds()),
            )

    def _closing_note(self) -> str:
        c = self.counts
        return (
            f"Found {c.get('found', 0)} openings, kept {c.get('kept', 0)} after the "
            f"sponsorship check, and ruled out {c.get('excluded', 0)} — each with the "
            "sentence that caused it."
        )

    async def _run_phases(self) -> None:
        cfg = settings.get_settings()
        want = int(self.params.get("count", cfg.default_job_count))

        # --- preflight ---------------------------------------------------
        t0 = await self._start("preflight")
        fb = context_loader.load(force=True)
        workspace_sync.bootstrap_tracker()
        ghosted = workspace_sync.age_applications()
        gate = D.TrackerGate()
        provider = await registry.resolve(force=True)
        llm_ok, llm_why = await provider.available()
        if not llm_ok:
            await self._log(
                "Running without an AI model — job finding, the sponsorship check, "
                "link checking and scoring all still work.", stage="preflight",
            )
        await self._finish(
            "preflight", t0,
            f"{len(fb.files)} fact files loaded; {len(gate.pairs)} past applications "
            f"will not be shown again" + (f"; {ghosted} marked ghosted" if ghosted else ""),
        )

        # --- source ------------------------------------------------------
        t0 = await self._start("source", items=6)
        sources = []
        if cfg.enable_ats_boards:
            sources += ats_sources.ALL
        if cfg.enable_feeds:
            sources += feed_sources.FREE
        if cfg.enable_workspace_import:
            sources += feed_sources.WORKSPACE
        sources += [s for s in feed_sources.KEYED if _keyed_ready(s, cfg)]

        titles = self.params.get("titles") or _default_titles()
        found, report = await gather_sources(sources, titles=titles)
        self.postings = found
        self.source_report = report
        self.counts["found"] = len(found)
        ok_sources = [r for r in report if r["ok"] and r["count"]]
        await self._finish(
            "source", t0,
            f"{len(found)} openings from {len(ok_sources)} sources", items=len(report),
        )

        if not found:
            self.counts.update(kept=0, excluded=0)
            await self._log("No openings came back. Check the source settings.", stage="source")
            return

        # --- normalize ---------------------------------------------------
        t0 = await self._start("normalize", items=len(self.postings))
        self.postings, dupes = D.dedupe(self.postings)
        await self._finish("normalize", t0, f"{dupes} duplicates removed", items=dupes + len(self.postings))

        # --- hard filter -------------------------------------------------
        t0 = await self._start("hard_filter", items=len(self.postings))
        self.postings, cut = D.hard_filter(self.postings)
        self._exclude(cut)
        await self._finish("hard_filter", t0,
                           f"{len(cut)} dropped as too senior, too many years, or outside the US")

        # Backfill missing ad text BEFORE the gate: the gate can only screen what
        # the text says, and a role imported from SUMMARY.md arrives with a link
        # but no text.
        filled = await D.backfill_jd(self.postings)
        if filled:
            await self._log(f"Fetched the ad text for {filled} postings that arrived without it.",
                            stage="sponsorship")

        # --- GATE: sponsorship -------------------------------------------
        t0 = await self._start("sponsorship", items=len(self.postings))
        verdicts: dict[str, Any] = {}
        kept: list[JobPosting] = []
        cut = []
        for p in self.postings:
            v = D.sponsorship_gate(p)
            if v.excluded:
                cut.append(ExcludedJob(
                    company=p.company, role_title=p.role_title, url=p.url,
                    stage="sponsorship", why=v.reason_label,
                    triggering_sentence=v.triggering_sentence,
                ))
            else:
                verdicts[p.source_id] = v
                kept.append(p)
        self._exclude(cut)
        self.postings = kept
        tiers = {t: sum(1 for v in verdicts.values() if v.tier.value == t) for t in "SABC"}
        await self._finish(
            "sponsorship", t0,
            f"{len(cut)} ruled themselves out; kept {len(kept)} "
            f"(S:{tiers['S']} A:{tiers['A']} B:{tiers['B']} C:{tiers['C']})",
        )

        # --- GATE: tracker -----------------------------------------------
        t0 = await self._start("tracker", items=len(self.postings))
        self.postings, cut = gate.split(self.postings)
        self._exclude(cut)
        await self._finish("tracker", t0, f"{len(cut)} already applied to or in cooldown")

        # Rank early on deterministic signals so link checking and the expensive
        # LLM phases only ever touch the shortlist.
        prelim = [
            ScoredJob(job=p, sponsor=verdicts[p.source_id],
                      score=scoring.score_job(p, verdicts[p.source_id], fb=fb))
            for p in self.postings
        ]
        prelim = scoring.rank(prelim)
        shortlist = prelim[: max(want * 2, want + 5)]

        # --- GATE: links -------------------------------------------------
        if cfg.verify_links and shortlist:
            t0 = await self._start("link_verify", items=len(shortlist))

            async def on_progress(done: int, total: int) -> None:
                pass

            statuses = await D.verify_links(
                [s.job for s in shortlist],
                concurrency=cfg.max_parallel_http // 2 or 2,
                per_host_delay=cfg.link_check_delay_s,
            )
            alive, dead = [], []
            for s in shortlist:
                st = statuses.get(s.job.source_id, LinkStatus.NEEDS_CHECK)
                s.link_status = st
                if st in (LinkStatus.EXPIRED, LinkStatus.BROKEN):
                    dead.append(ExcludedJob(
                        company=s.job.company, role_title=s.job.role_title, url=s.job.url,
                        stage="link", why=f"The apply link is {st.value.lower()}.",
                        triggering_sentence=s.job.url,
                    ))
                else:
                    alive.append(s)
            self._exclude(dead)
            shortlist = alive
            await self._finish("link_verify", t0, f"{len(dead)} dead links removed")
        else:
            await self._skip("link_verify", "Link checking is turned off in settings.")

        # --- LLM phases ---------------------------------------------------
        top = shortlist[:want]
        if llm_ok:
            from . import enrich
            await enrich.run(self, top, fb=fb, provider=provider)
        else:
            for key in ("jd_parse", "company_intel", "skill_predict"):
                await self._skip(key, llm_why)
            for s in top:
                s.jd = D.parse_jd_keywords(s.job)

        # --- score ---------------------------------------------------------
        t0 = await self._start("fit_score", items=len(top))
        for s in top:
            # Text scraped off a careers page is not a clean job ad; scoring its
            # navigation as requirements produces confident nonsense.
            noisy = bool(s.job.raw.get("jd_fetched")) and (
                s.jd is None or s.jd.source == "keywords"
            )
            s.score = scoring.score_job(
                s.job, s.sponsor, jd=s.jd,
                skill_override=(s.prediction.must_have_coverage * 100) if s.prediction else None,
                skill_note=(s.prediction.rationale if s.prediction else ""),
                fb=fb,
            )
            s.recommendation = scoring.recommendation(
                s.score.total, s.score.competition,
                has_jd=len(s.job.jd_text.strip()) > 200 and not noisy,
            )
            if noisy:
                s.score.evidence["skill_match"] = (
                    "The ad text was read off the careers page, so it is not scored "
                    "on keywords. Open the link to judge this one."
                )
            s.ghost_flags = scoring.ghost_flags(s.job)
        self.scored = scoring.rank(top)
        self.counts["kept"] = len(self.scored)
        self.counts["excluded"] = len(self.excluded)
        await self._finish("fit_score", t0, f"{len(self.scored)} jobs ranked, best matches first")

        # --- persist --------------------------------------------------------
        t0 = await self._start("persist")
        self._persist_jobs()
        workspace_sync.write_summary(
            scored=self.scored, excluded=self.excluded,
            last_run_note=self._closing_note(),
            study_items=self._study_demand(),
        )
        workspace_sync.append_scan_history(
            found=self.counts.get("found", 0), kept=len(self.scored),
            excluded=len(self.excluded), prepared=0,
            note="dashboard scan",
        )
        workspace_sync.sync_applied_companies()
        await self._finish("persist", t0, "Your summary page is up to date")

    # -- helpers ------------------------------------------------------------
    def _persist_jobs(self) -> None:
        for s in self.scored:
            j = s.job
            jid = f"{j.source}:{j.source_id}"
            db.connect().execute(
                "INSERT INTO jobs (id, source, source_id, company, company_key, role_title,"
                " role_key, url, location, remote, department, posted_at, jd_text,"
                " content_hash, raw_json, first_seen, last_seen)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
                " ON CONFLICT(company_key, role_key, content_hash) DO UPDATE SET"
                " last_seen=excluded.last_seen, url=excluded.url, jd_text=excluded.jd_text",
                (jid, j.source, j.source_id, j.company, legacy.normalize_company(j.company),
                 j.role_title, legacy.track.norm(j.role_title), j.url, j.location,
                 int(j.remote), j.department,
                 j.posted_at.isoformat() if j.posted_at else None,
                 j.jd_text, j.content_hash, db.dumps(j.raw), db.now(), db.now()),
            )
            db.connect().execute(
                "INSERT INTO job_analysis (job_id, run_id, tier, verdict, reason,"
                " reason_label, triggering_sentence, everify, cap_exempt, h1b_approvals,"
                " link_status, score, score_json, jd_json, research_json, prediction_json,"
                " recommendation, ghost_flags, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
                " ON CONFLICT(job_id) DO UPDATE SET run_id=excluded.run_id,"
                " tier=excluded.tier, score=excluded.score, score_json=excluded.score_json,"
                " jd_json=excluded.jd_json, research_json=excluded.research_json,"
                " prediction_json=excluded.prediction_json,"
                " recommendation=excluded.recommendation, updated_at=excluded.updated_at",
                (jid, self.id, s.sponsor.tier.value, s.sponsor.verdict, s.sponsor.reason,
                 s.sponsor.reason_label, s.sponsor.triggering_sentence,
                 int(s.sponsor.everify), int(s.sponsor.cap_exempt), s.sponsor.h1b_approvals,
                 s.link_status.value, s.score.total, db.dumps(s.score.model_dump(mode="json")),
                 db.dumps(s.jd.model_dump(mode="json") if s.jd else {}),
                 db.dumps(s.research.model_dump(mode="json") if s.research else {}),
                 db.dumps(s.prediction.model_dump(mode="json") if s.prediction else {}),
                 s.recommendation, db.dumps(s.ghost_flags), db.now()),
            )

    def _study_demand(self) -> list[tuple[str, int]]:
        """Skills wanted by the most jobs that she does not have. Ranked by demand."""
        fb = context_loader.load()
        counts: dict[str, int] = {}
        for s in self.scored:
            terms = [r.keyword or r.text for r in (s.jd.must_haves if s.jd else [])]
            for t in terms:
                if not fb.claimable(t.lower()):
                    counts[t] = counts.get(t, 0) + 1
        return sorted(counts.items(), key=lambda kv: -kv[1])


def _keyed_ready(source: Any, cfg: settings.Settings) -> bool:
    if source.name == "adzuna":
        return bool(cfg.enable_adzuna and cfg.adzuna_app_id and cfg.adzuna_app_key)
    if source.name == "usajobs":
        return bool(cfg.enable_usajobs and cfg.usajobs_email)
    return False


def _default_titles() -> list[str]:
    return [
        "Data Engineer", "Machine Learning Engineer", "Software Engineer",
        "Analytics Engineer", "AI Engineer", "Test Automation Engineer",
    ]


# --------------------------------------------------------------------------
# registry of live runs
# --------------------------------------------------------------------------
RUNS: dict[str, Run] = {}
_TASKS: dict[str, asyncio.Task] = {}


def start(params: dict[str, Any] | None = None) -> Run:
    run = Run(params)
    RUNS[run.id] = run
    _TASKS[run.id] = asyncio.create_task(run.execute())
    return run


def get(run_id: str) -> Run | None:
    return RUNS.get(run_id)


async def wait(run_id: str) -> None:
    """Block until a run finishes. Used by the scheduled morning brief, which
    has to know the scan is done before it starts building resumes."""
    task = _TASKS.get(run_id)
    if task is not None:
        try:
            await task
        except asyncio.CancelledError:
            pass


def cancel(run_id: str) -> bool:
    task = _TASKS.get(run_id)
    if task and not task.done():
        task.cancel()
        r = RUNS.get(run_id)
        if r:
            r.status = RunStatus.CANCELLED
            r._save()
        return True
    return False
