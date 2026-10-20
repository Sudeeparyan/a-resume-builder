"""The Daily Search pipeline: find jobs, then take each new job end to end.

Annie chooses on the Daily Search page how many jobs to find, where to look and which helpers
run. Every job then goes through the same chain, one step after the other: the posting is
re-read (a closed or now-refusing one gets nothing more), company research with the
hiring-manager view and her requirement check (services/fit.py), the tailored resume (verified
registry items plus predicted ones for her Assurance review), the one-page US Letter PDF, an
independent review of that PDF, the study plan and the ready-to-submit check
(services/readiness.py). This module checks that choice, runs it on one background thread and
reports progress step by step. Every step goes through the same AgentRunner and Resume Studio
paths as the rest of the app, so the sponsorship gate, the never-re-apply rules, the paid-call
limit and the Assurance review all still apply. Nothing is ever submitted.

Time and token figures are estimates. ``FIND`` and ``STEPS`` hold first-run numbers for a
local app (Claude Code · sonnet); every finished run records how long its steps really took,
and ``speeds`` turns that into a per-AI factor so the next estimate is closer. The page does
the arithmetic (``estimatePipeline`` in the frontend).

Ported from the Template (October 2026). Not taken: its follow-up search passes, the overnight
hunt, salary checks, market packs and durable stage records.
"""

from __future__ import annotations

import json
import statistics
import threading
import time
import uuid

from backend.services.agents import DEFAULT_DISCOVERY_JOBS, MAX_DISCOVERY_JOBS

SOURCES = [
    {"id": "default", "label": "Web search", "ai": True,
     "what": "The AI searches job sites for fresh US postings that fit you, best match first."},
    {"id": "balanced_five", "label": "Balanced mix", "ai": True,
     "what": "The AI looks for a mix of startups, mid-size and large companies; mid-size and large ones "
             "need an H-1B record or a posting that offers sponsorship."},
    {"id": "portals", "label": "My company list + sponsor boards", "ai": False,
     "what": "Reads the career feeds of your tracked companies and of proven H-1B sponsors, with the full "
             "posting text. The search itself uses no AI. Every eligible match is saved; the best fits are "
             "prepared, one per company."},
]
SOURCE_IDS = [source["id"] for source in SOURCES]

# Finding jobs happens once per run; its cost grows a little with each job asked for.
FIND = {
    "find_ai": {"minutes": 5.0, "minutes_per_job": 0.5, "tokens": 40000, "tokens_per_job": 6000, "budget_calls": 1},
    "find_pages": {"minutes": 8.0, "minutes_per_job": 0.1, "tokens": 0, "tokens_per_job": 0, "budget_calls": 0},
}

# The helpers that run once per job, in the order they run. ``budget_calls`` are the
# background AI calls a step makes; they count against the daily paid-call limit only
# when a paid AI serves them.
STEPS = [
    {"id": "posting", "label": "Posting still open", "ai": False, "web": True,
     "minutes": 0.3, "tokens": 0, "budget_calls": 0,
     "what": "Re-reads the posting's own page before any work starts, and runs the sponsorship gate on what "
             "it says now. A closed or refusing posting gets nothing more. No AI."},
    {"id": "research", "label": "Research & fit", "ai": True, "web": True,
     "minutes": 5.0, "tokens": 36000, "budget_calls": 3,
     "what": "Public company research, a hiring manager's view of the role (it never sees you), your profile "
             "against both, and the requirement check: each must-have marked met, partly met or missing "
             "from your registered evidence."},
    {"id": "tailor", "label": "Tailor resume", "ai": True, "web": False,
     "minutes": 3.0, "tokens": 22000, "budget_calls": 0,
     "what": "Picks your verified Projects and Skills for this job and suggests predicted items for you to "
             "keep or remove in Assurance. Experience, education and personal details never change."},
    {"id": "pdf", "label": "One-page PDF", "ai": False, "web": False,
     "minutes": 0.5, "tokens": 0, "budget_calls": 0,
     "what": "Builds the PDF and checks it is exactly one full US Letter page. No AI."},
    {"id": "review", "label": "Independent review", "ai": True, "web": False,
     "minutes": 1.5, "tokens": 12000, "budget_calls": 1,
     "what": "A fresh AI reads only the finished PDF and the posting, never your profile, and says what is met, "
             "partly met or missing, with a verdict."},
    {"id": "study_plan", "label": "Study plan", "ai": True, "web": False,
     "minutes": 1.5, "tokens": 8000, "budget_calls": 1,
     "what": "Lists what to learn before the interview. It never goes on your resume."},
    {"id": "ready", "label": "Ready-to-submit check", "ai": False, "web": False,
     "minutes": 0.2, "tokens": 0, "budget_calls": 0,
     "what": "Checks every gate again (open posting, sponsorship, fit, one page, the review, your Assurance "
             "decisions) and gives a readiness score. It is not a prediction of an interview. No AI."},
]
STEP_IDS = [step["id"] for step in STEPS]
STEP = {step["id"]: step for step in STEPS}
ON_DEMAND: tuple = ()
DEFAULT_STEPS = {step: step not in ON_DEMAND for step in STEP_IDS}
# A company with this many resumes already waiting gets no new one (as in the morning run).
MAX_WAITING_PER_COMPANY = 3

# Signed-in local apps: their calls count against her plan's usage limit, never an API bill.
LOCAL_APPS = ("kimi_cli", "codex", "claude_code", "antigravity_cli")
CLAUDE_MODELS = [
    ("sonnet", "Sonnet", "Balanced. Recommended for most days."),
    ("opus", "Opus", "Best writing. Slowest, and uses the most of your limit."),
    ("haiku", "Haiku", "Fastest and lightest on your limit. Simpler writing."),
]
MAX_LISTED_MODELS = 3
# How long an AI step takes compared with Claude Code · sonnet, before any run is measured.
MODEL_SPEED = {("claude_code", "sonnet"): 1.0, ("claude_code", "opus"): 1.5, ("claude_code", "haiku"): 0.6,
               ("codex", None): 1.2, ("kimi_cli", None): 1.3, ("antigravity_cli", None): 1.2}
FAST_NAMES = ("luna", "highspeed", "mini", "flash", "lite")
API_SPEED = 0.6  # a hosted API answers in one call, without an agent loop
ACTIVE = ("queued", "running")


class JobStopped(Exception):
    """A helper found that the job cannot go further (its posting closed); its later helpers are skipped."""


class Stopped(Exception):
    pass


def step_entry(done: dict, seconds: float) -> dict:
    """A helper's return as its progress entry: done, or skipped when it had nothing to work on."""
    extra = {k: v for k, v in done.items() if k != "skipped"}
    return {"state": "skipped" if done.get("skipped") else "done", "seconds": seconds, **extra}


def open_draft(studio, job_id: str, step: str, opened: bool) -> bool:
    """Open the application folder and Studio draft before the first helper that writes into them.

    The posting check comes first, so a closed posting never gets a folder.
    """
    if opened or step == "posting":
        return opened
    studio.open(job_id)
    return True


def default_speed(provider: str, model: str) -> float:
    if (provider, model) in MODEL_SPEED:
        return MODEL_SPEED[(provider, model)]
    base = MODEL_SPEED.get((provider, None), 1.0 if provider in LOCAL_APPS or provider == "auto" else API_SPEED)
    return round(base * 0.7, 2) if any(word in (model or "").casefold() for word in FAST_NAMES) else base


def local_models(provider_id: str) -> list:
    """The model choices for one local app: Claude's three, or the app's default plus what the plan lists."""
    from backend.ai import antigravity_cli, codex, kimi_cli

    if provider_id == "claude_code":
        return [{"id": m, "label": name, "hint": hint} for m, name, hint in CLAUDE_MODELS]
    if provider_id == antigravity_cli.ID:
        return [{"id": antigravity_cli.RUNTIME, "label": "Default",
                 "hint": "Antigravity's usual model. A safe choice if you are not sure."}] + [
            {"id": m, "label": m, "hint": ""} for m in antigravity_cli.MODELS if m != antigravity_cli.RUNTIME
        ][:MAX_LISTED_MODELS]
    if provider_id == codex.ID:
        listed = [m for m in codex.listed_models() if m["id"] not in codex.MODELS][:MAX_LISTED_MODELS]
        return [{"id": codex.MODELS[0], "label": "Default",
                 "hint": "Codex picks its usual model. A safe choice if you are not sure."}] + listed
    listed = kimi_cli.listed_models()
    default = next((m["label"] for m in listed if m["default"]), None)
    others = [m for m in listed if not m["default"]][:MAX_LISTED_MODELS]
    return [{"id": kimi_cli.MODELS[0], "label": "Default",
             "hint": "Kimi Code's usual model" + (f" ({default})." if default else ".")}] + [
        {"id": m["id"], "label": m["label"],
         "hint": "Faster replies." if "highspeed" in m["id"].casefold() else ""} for m in others]


def find_key(source: str) -> str:
    return "find_ai" if next(s for s in SOURCES if s["id"] == source)["ai"] else "find_pages"


def find_seconds(key: str, jobs: int) -> float:
    return (FIND[key]["minutes"] + FIND[key]["minutes_per_job"] * jobs) * 60


def busy(workspace) -> bool:
    """True while a pipeline or any agent run is queued or running."""
    try:
        with workspace.connect() as db:
            if db.execute("SELECT 1 FROM agent_runs WHERE state IN ('queued','running') LIMIT 1").fetchone():
                return True
            table = db.execute("SELECT 1 FROM sqlite_master WHERE name='pipeline_runs'").fetchone()
            return bool(table and db.execute(
                "SELECT 1 FROM pipeline_runs WHERE state IN ('queued','running') LIMIT 1").fetchone())
    except Exception:
        return False


def _company(name) -> str:
    return "".join(ch for ch in str(name or "").casefold() if ch.isalnum())


def choose(jobs: list[dict], candidates: list[str], target: int,
           per_company: int = MAX_WAITING_PER_COMPANY) -> list[str]:
    """Which found jobs to prepare: best fit first, one per company per run, and none for a
    company that already has ``per_company`` resumes waiting (the morning run's rule)."""
    by_id = {job["id"]: job for job in jobs}
    waiting: dict[str, int] = {}
    for job in jobs:
        if job.get("folder") and job.get("status") in {"saved", "prepared"} and job["id"] not in candidates:
            waiting[_company(job.get("company"))] = waiting.get(_company(job.get("company")), 0) + 1
    ranked = sorted((by_id[i] for i in candidates if i in by_id),
                    key=lambda job: -(job.get("fit_score") if isinstance(job.get("fit_score"), (int, float)) else -1))
    chosen, used = [], set()
    for job in ranked:
        key = _company(job.get("company"))
        if key in used or waiting.get(key, 0) >= per_company:
            continue
        chosen.append(job["id"])
        used.add(key)
        if len(chosen) >= target:
            break
    return chosen


class Pipeline:
    def __init__(self, services, runner, studio, poll_seconds: float = 2.0):
        self.s, self.w, self.runner, self.studio = services, services.w, runner, studio
        self.poll = poll_seconds
        self.lock = threading.Lock()
        self.thread = None
        with self.w.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS pipeline_runs(
                id TEXT PRIMARY KEY, state TEXT NOT NULL, config TEXT NOT NULL,
                progress TEXT NOT NULL DEFAULT '{}', error TEXT,
                stop_requested INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL, finished_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_pipeline_runs_created ON pipeline_runs(created_at);
            """)

    # ----- what the page shows -------------------------------------------------

    def providers(self) -> list:
        """Every AI the page can offer: Auto, the local apps always (ready or not), hosted APIs only when keyed."""
        from backend.ai import catalog, codex, kimi_cli, provider_label, ready_providers

        ready = ready_providers(self.w.root)
        signed_in = {codex.ID: codex.signed_in, kimi_cli.ID: kimi_cli.signed_in}
        listed = [self._auto_entry(ready)]
        for provider_id in LOCAL_APPS:
            label = provider_label(provider_id)
            installed = bool(ready.get(provider_id))
            note = None
            if provider_id == kimi_cli.ID and not installed and kimi_cli.extension_only():
                note = ("Kimi Code for VS Code is installed, but this app needs the Kimi Code terminal app. "
                        f"In PowerShell run: {kimi_cli.INSTALL_COMMAND} (it uses the same sign-in), "
                        "then reload this page.")
            elif not installed:
                note = f"{label} is not installed on this PC. Install it and sign in, then reload this page."
            elif provider_id in signed_in and not signed_in[provider_id]():
                note = f"{label} may not be signed in. If a step fails, open {label}, sign in and try again."
            listed.append({
                "id": provider_id, "label": label, "kind": "local", "ready": installed, "web": True,
                "cost": "Uses your plan's usage limit. No extra bill.", "note": note,
                "models": local_models(provider_id),
            })
        for provider_id in catalog.PROVIDERS:
            engine = self.runner.gateway.providers.get(provider_id)
            if not ready.get(provider_id) or engine is None:
                continue
            listed.append({
                "id": provider_id, "label": provider_label(provider_id), "kind": "api", "ready": True,
                "web": "web" in engine.capabilities,
                "cost": "Pay per use on your API key.",
                "note": None if "web" in engine.capabilities else
                "Cannot search the web, so finding jobs and company research use another AI that can.",
                "models": [{"id": m, "label": m, "hint": ""} for m in list(engine.models)[:8]],
            })
        return listed

    def _auto_entry(self, ready: dict) -> dict:
        """Auto on the page: the route in order, which plans rest and until when."""
        from backend.ai import paid_gate, router

        policy = router.policy_from(self.s.pref("ai_preferences", {}) or {})
        blocked = paid_gate(self.s)("azure_openai")
        route = router.status(self.w.root, policy, ready_map=ready, paid={"block": blocked})
        usable = [row for row in route if row["enabled"] and row["ready"]]
        resting = [f"{row['label']} rests until {row['resting']['until_text']}" for row in usable if row["resting"]]
        steps = " → ".join(row["label"] + (" (paid)" if row["paid"] else "") for row in usable) or "nothing set up yet"
        return {
            "id": router.ID, "label": router.LABEL, "kind": "auto", "ready": bool(ready.get(router.ID)), "web": True,
            "cost": "Uses your Kimi, Codex, Claude and Antigravity plans first. Azure (paid) only when all are resting.",
            "note": ("; ".join(resting) + ". The next plan takes over." if resting else None),
            "models": [{"id": router.ID, "label": "Auto", "hint": steps}],
            "route": route,
        }

    def speeds(self, providers: list) -> dict:
        """Per AI and model, how long each step takes compared with the first-run estimate."""
        learned = self._learned()
        tailor_tokens = self._tailor_tokens()
        speeds = {}
        for provider in providers:
            for model in provider["models"]:
                key = provider["id"] + ":" + model["id"]
                base = default_speed(provider["id"], model["id"])
                speeds[key] = {}
                for step in (*FIND, *STEP_IDS):
                    ratios = learned.get((key, step))
                    ai = step == "find_ai" or (step in STEP and STEP[step]["ai"])
                    speeds[key][step] = (
                        {"factor": round(statistics.median(ratios), 2), "learned": True, "runs": len(ratios)}
                        if ratios else {"factor": base if ai else 1.0, "learned": False, "runs": 0}
                    )
                if key in tailor_tokens:
                    speeds[key]["tailor"]["tokens"] = tailor_tokens[key]
        return speeds

    def _tailor_tokens(self) -> dict:
        """Measured tokens per tailored resume, per provider:model (the tailor's specialist reports usage)."""
        with self.w.connect() as db:
            rows = db.execute(
                "SELECT provider, model, input_tokens + COALESCE(output_tokens, 0) FROM ai_calls "
                "WHERE cache_key='usage' AND action='specialist:job_tailor' AND input_tokens IS NOT NULL "
                "ORDER BY created_at DESC LIMIT 200").fetchall()
        seen = {}
        for provider, model, tokens in rows:
            seen.setdefault(f"{provider}:{model}", []).append(tokens)
        return {key: int(statistics.median(values[:10])) for key, values in seen.items()}

    def _learned(self) -> dict:
        """Measured seconds ÷ first-run estimate, per (provider:model, step), from recent finished runs."""
        ratios = {}
        with self.w.connect() as db:
            rows = db.execute(
                "SELECT config, progress FROM pipeline_runs WHERE state IN ('completed','stopped') "
                "ORDER BY created_at DESC LIMIT 20").fetchall()
        for row in rows:
            try:
                config, progress = json.loads(row["config"]), json.loads(row["progress"])
            except (TypeError, ValueError):
                continue
            key = config.get("provider", "") + ":" + config.get("model", "")

            def add(step, seconds, expected):
                if seconds and expected:
                    ratios.setdefault((key, step), []).append(min(5.0, max(0.1, seconds / expected)))

            found = progress.get("find") or {}
            if found.get("state") == "done" and config.get("source") in SOURCE_IDS:
                step = find_key(config["source"])
                add(step, found.get("seconds"), find_seconds(step, progress.get("jobs_target") or config.get("count", 5)))
            for job in progress.get("jobs") or []:
                for step, state in (job.get("steps") or {}).items():
                    if step in STEP and state.get("state") == "done" and not state.get("quick"):
                        add(step, state.get("seconds"), STEP[step]["minutes"] * 60)
        return ratios

    def preferences(self, providers: list | None = None) -> dict:
        """The saved search (count, where to look, helpers) with the AI chosen in Settings."""
        from backend.ai import main_choice, ready_providers

        providers = providers if providers is not None else self.providers()
        stored = self.s.pref("pipeline_preferences", {}) or {}
        by_id = {p["id"]: p for p in providers}
        provider, stored_model = main_choice(self.s.pref("ai_preferences", {}) or {}, ready_providers(self.w.root))
        if provider not in by_id or not by_id[provider]["ready"]:
            first = next((p for p in providers if p["ready"]), providers[0] if providers else None)
            provider, stored_model = (first["id"], first["models"][0]["id"]) if first else ("", "")
        models = [m["id"] for m in by_id.get(provider, {}).get("models", [])]
        model = stored_model if stored_model in models else (models[0] if models else "")
        source = stored.get("source") or (self.s.pref("discovery_preferences", {}) or {}).get("preset") or "default"
        count = stored.get("count") or DEFAULT_DISCOVERY_JOBS
        return {
            "count": min(int(count), MAX_DISCOVERY_JOBS),
            "source": source if source in SOURCE_IDS else "default",
            "provider": provider, "model": model,
            "steps": {step: bool((stored.get("steps") or {}).get(step, DEFAULT_STEPS[step])) for step in STEP_IDS},
        }

    def overview(self) -> dict:
        providers = self.providers()
        return {
            "sources": SOURCES, "find": FIND, "steps": STEPS, "max_jobs": MAX_DISCOVERY_JOBS,
            "providers": providers, "speeds": self.speeds(providers),
            "preferences": self.preferences(providers),
            **self.status(),
        }

    def status(self) -> dict:
        import shutil

        budget = self.runner.cache.stats()
        return {
            # The PDF step (and the tailor's own page fit) need the Tectonic compiler.
            "tools": {"pdf": bool(shutil.which("tectonic"))},
            # The daily limit counts paid calls only; calls on her plans are shown beside it.
            "budget": {"limit": budget["daily_call_limit"], "used": budget["paid_calls_today"],
                       "remaining": budget["remaining_calls"], "paid_only": True,
                       "free_used": budget["free_calls_today"]},
            "plan": {"remaining_today": self.s.goals()["remaining_today"]},
            "current": self._latest(active=True),
            "last": self._latest(active=False),
        }

    # ----- choosing and starting ---------------------------------------------

    def validate(self, values: dict, require_ready: bool = True) -> dict:
        count = values.get("count", DEFAULT_DISCOVERY_JOBS)
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= MAX_DISCOVERY_JOBS:
            raise ValueError(f"Choose between 1 and {MAX_DISCOVERY_JOBS} jobs.")
        source = values.get("source") or "default"
        if source not in SOURCE_IDS:
            raise ValueError("Choose where to look: web search, balanced mix or your company list.")
        providers = {p["id"]: p for p in self.providers()}
        if not values.get("provider"):
            # No AI named: the one chosen in Settings does the work.
            chosen = self.preferences(list(providers.values()))
            values = {**values, "provider": chosen["provider"], "model": values.get("model") or chosen["model"]}
        provider = providers.get(values.get("provider") or "")
        if provider is None:
            raise ValueError("Choose one of the AI apps listed on the page.")
        model = values.get("model") or ""
        if model not in [m["id"] for m in provider["models"]]:
            raise ValueError(f"Choose a model for {provider['label']}.")
        if require_ready and not provider["ready"]:
            raise ValueError(provider["note"] or f"{provider['label']} is not ready on this PC. Choose another AI.")
        steps = values.get("steps") or {}
        return {
            "count": count, "source": source, "provider": provider["id"], "model": model,
            "steps": {step: bool(steps.get(step, DEFAULT_STEPS[step])) for step in STEP_IDS},
            "include_unprepared": bool(values.get("include_unprepared")),
        }

    def save_preferences(self, values: dict) -> dict:
        config = self.validate(values, require_ready=False)
        self._remember(config)
        return config

    def _remember(self, config: dict) -> None:
        # The AI is Settings' choice, never remembered here; a one-run choice from the chat stays one run.
        self.s.set_pref("pipeline_preferences", {k: config[k] for k in ("count", "source", "steps")})
        # One "where to look" everywhere: the chat's "find jobs" reads this preference too.
        self.s.set_pref("discovery_preferences", {"preset": config["source"]})

    def start(self, values: dict) -> dict:
        config = self.validate(values)
        with self.lock:
            if self._latest(active=True):
                raise ValueError("A search is already running. Wait for it to finish, or stop it first.")
            with self.w.connect() as db:
                if db.execute("SELECT 1 FROM agent_runs WHERE kind='discovery' AND state IN ('queued','running')").fetchone():
                    raise ValueError("A job search started elsewhere is still running. Try again when it finishes.")
            remaining = self.s.goals()["remaining_today"]
            if remaining <= 0:
                raise ValueError("Today's plan is already complete, so there is nothing left to prepare. "
                                 "Raise your plan with Edit target to search for more.")
            target = min(config["count"], remaining)
            id = uuid.uuid4().hex
            progress = {
                "stage": "Waiting to start", "jobs_target": target, "started_epoch": time.time(),
                "find": {"state": "waiting"}, "jobs": [],
            }
            now = self.s.now()
            with self.w.connect() as db:
                db.execute(
                    "INSERT INTO pipeline_runs(id,state,config,progress,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                    (id, "queued", json.dumps(config), json.dumps(progress), now, now))
                self.w.record_event(db, "pipeline_started", run_id=id, **config)
            self._remember(config)
            from backend import telemetry

            self.thread = threading.Thread(target=telemetry.carry(self._traced), args=(id,), name="career-pipeline", daemon=True)
            self.thread.start()
        return self.get(id)

    def stop(self, id: str) -> dict:
        with self.w.connect() as db:
            db.execute("UPDATE pipeline_runs SET stop_requested=1, updated_at=? WHERE id=? AND state IN ('queued','running')",
                       (self.s.now(), id))
        return self.get(id)

    def recover(self) -> None:
        """A run the app stopped in the middle carries on from where it was after a restart."""
        with self.w.connect() as db:
            rows = db.execute("SELECT id FROM pipeline_runs WHERE state IN ('queued','running') ORDER BY created_at").fetchall()
        if rows:
            def resume():
                for row in rows:
                    self._traced(row["id"])
            from backend import telemetry

            self.thread = threading.Thread(target=telemetry.carry(resume), name="career-pipeline-recovery", daemon=True)
            self.thread.start()

    def get(self, id: str) -> dict | None:
        with self.w.connect() as db:
            row = db.execute("SELECT * FROM pipeline_runs WHERE id=?", (id,)).fetchone()
        return self._public(row) if row else None

    def _latest(self, active: bool) -> dict | None:
        states = ACTIVE if active else ("completed", "failed", "stopped")
        with self.w.connect() as db:
            row = db.execute(
                f"SELECT * FROM pipeline_runs WHERE state IN ({','.join('?' * len(states))}) ORDER BY created_at DESC, rowid DESC LIMIT 1",
                states).fetchone()
        return self._public(row) if row else None

    @staticmethod
    def _public(row) -> dict:
        return {
            "id": row["id"], "state": row["state"], "config": json.loads(row["config"]),
            "progress": json.loads(row["progress"] or "{}"), "error": row["error"],
            "stop_requested": bool(row["stop_requested"]), "created_at": row["created_at"],
            "finished_at": row["finished_at"],
        }

    # ----- running -------------------------------------------------------------

    def _save(self, id, progress, state="running", error=None, finished=False):
        now = self.s.now()
        with self.w.connect() as db:
            db.execute(
                "UPDATE pipeline_runs SET state=?, progress=?, error=?, updated_at=?, finished_at=COALESCE(?, finished_at) WHERE id=?",
                (state, json.dumps(progress, ensure_ascii=False), error, now, now if finished else None, id))

    def _stop_requested(self, id) -> bool:
        with self.w.connect() as db:
            row = db.execute("SELECT stop_requested FROM pipeline_runs WHERE id=?", (id,)).fetchone()
        return bool(row and row[0])

    def _traced(self, id: str) -> None:
        from backend import telemetry

        with telemetry.bind(profile_root=self.w.root, run={"id": f"pipeline:{id}", "kind": "pipeline"}):
            with telemetry.span("pipeline.run", **{"career.pipeline_id": id}) as current:
                self._run(id)
                with self.w.connect() as db:
                    row = db.execute("SELECT state,error FROM pipeline_runs WHERE id=?", (id,)).fetchone()
                if row:
                    telemetry.set_attributes(current, **{"career.run_state": row["state"]})
                    if row["state"] == "failed":
                        telemetry.mark_failed(current, row["error"])

    def _run(self, id: str) -> None:
        with self.w.connect() as db:
            row = db.execute("SELECT * FROM pipeline_runs WHERE id=?", (id,)).fetchone()
        config, progress = json.loads(row["config"]), json.loads(row["progress"])
        try:
            if (progress.get("find") or {}).get("state") != "done":
                self._find(id, config, progress)
            steps = [step for step in STEP_IDS if config["steps"].get(step)]
            total = len(progress["jobs"])
            for number, job in enumerate(progress["jobs"], 1):
                self._job(id, config, progress, job, steps, number, total)
            verdicts = [(job["steps"].get("ready") or {}).get("verdict") for job in progress["jobs"]]
            if any(verdicts):
                progress["ready"] = {key: verdicts.count(key) for key in ("ready", "review", "blocked")}
            stopped = self._stop_requested(id)
            progress["stage"] = "Stopped" if stopped else "Done"
            progress["finished_epoch"] = time.time()
            self._save(id, progress, "stopped" if stopped else "completed", finished=True)
            with self.w.connect() as db:
                self.w.record_event(db, "pipeline_finished", run_id=id, state="stopped" if stopped else "completed",
                                    jobs=total)
        except Stopped:
            progress["stage"] = "Stopped"
            progress["finished_epoch"] = time.time()
            self._save(id, progress, "stopped", finished=True)
        except Exception as exc:  # the page must always learn how the run ended
            progress["stage"] = "Stopped by a problem"
            progress["finished_epoch"] = time.time()
            self._save(id, progress, "failed", error=str(exc)[:1500], finished=True)
        finally:
            try:
                self.s.export_state()
            except Exception:
                pass

    def _find(self, id, config, progress) -> None:
        progress["find"] = {"state": "running", "started_epoch": time.time()}
        progress["stage"] = "Finding jobs"
        self._save(id, progress)
        provider, model = self._web_choice(config)
        target = progress["jobs_target"]
        started = time.time()
        ai_search = next(s for s in SOURCES if s["id"] == config["source"])["ai"]
        try:
            record = self._agent("discovery", None, provider, model, preset=config["source"],
                                 count=target if ai_search else None)
        except Exception as exc:
            progress["find"] = {"state": "failed", "seconds": round(time.time() - started, 1), "error": str(exc)[:600]}
            self._save(id, progress)
            raise ValueError("Finding jobs did not finish: " + str(exc)) from None
        result = record.get("result") or {}
        added = list(dict.fromkeys(result.get("added_job_ids") or []))
        jobs = self.w.jobs()
        candidates = list(added)
        if config.get("include_unprepared"):
            # Saved jobs an earlier run found but never prepared join this one.
            candidates += [j["id"] for j in jobs if j.get("status") == "saved" and not j.get("folder") and j["id"] not in candidates]
        ids = choose(jobs, candidates, target)
        note = f"Found {len(added)} new job{'s' if len(added) != 1 else ''}"
        if len(added) > len(ids):
            note += f"; preparing the best {len(ids)} (one per company; the rest stay on your list)"
        elif len(ids) < target:
            note += f" (asked for {target}; only jobs that pass every check are saved)"
        progress["find"] = {"state": "done", "seconds": round(time.time() - started, 1), "found": len(added),
                            "note": note, "run_id": record.get("id")}
        prepared = []
        for job_id in ids:
            job = self.w.get_job(job_id)
            prepared.append({"id": job_id, "company": job["company"], "title": job["title"], "fit": job.get("fit_score"),
                             "steps": {step: {"state": "waiting"} for step in STEP_IDS if config["steps"].get(step)}})
        progress["jobs"] = prepared
        self._save(id, progress)

    def _job(self, id, config, progress, job, steps, number, total) -> None:
        """Every switched-on helper for one job, in order."""
        state = {"stopped": None, "opened": False}
        for step in steps:
            state = self._job_step(id, config, progress, job, step, number, total, state)

    def _job_step(self, id, config, progress, job, step, number, total, state) -> dict:
        """One helper for one job. ``state`` carries why the job stopped and whether its draft is open."""
        stopped, opened = state.get("stopped"), state.get("opened", False)
        if self._stop_requested(id):
            job["steps"][step] = {"state": "skipped"}
            return {"stopped": stopped, "opened": opened}
        if stopped:
            job["steps"][step] = {"state": "skipped", "note": stopped}
            return {"stopped": stopped, "opened": opened}
        try:
            issue = self._preparation_issue(job["id"])
            if step != "posting" and issue:
                raise JobStopped(issue)
            opened = open_draft(self.studio, job["id"], step, opened)
        except JobStopped as exc:
            job["steps"][step] = {"state": "failed", "error": str(exc)}
            self._save(id, progress)
            return {"stopped": str(exc), "opened": opened}
        except Exception as exc:
            stopped = "Could not open this job's resume: " + str(exc)[:500]
            job["steps"][step] = {"state": "failed", "error": stopped}
            self._save(id, progress)
            return {"stopped": stopped, "opened": opened}
        progress["stage"] = f"{STEP[step]['label']} for {job['company']} (job {number} of {total})"
        job["steps"][step] = {"state": "running", "started_epoch": time.time()}
        self._save(id, progress)
        started = time.time()
        try:
            done = self.run_step(step, job["id"], config)
            job["steps"][step] = step_entry(done, round(time.time() - started, 1))
        except JobStopped as exc:
            stopped = str(exc)
            job["steps"][step] = {"state": "failed", "seconds": round(time.time() - started, 1), "error": stopped}
        except Exception as exc:
            job["steps"][step] = {"state": "failed", "seconds": round(time.time() - started, 1), "error": str(exc)[:600]}
        self._save(id, progress)
        return {"stopped": stopped, "opened": opened}

    def _preparation_issue(self, job_id) -> str:
        """Why a job must not be prepared any further, or ""."""
        try:
            job = self.w.get_job(job_id)
        except (KeyError, ValueError):
            return "The job was removed, so nothing more was prepared."
        if job.get("deleted_at"):
            return "The job was removed, so nothing more was prepared."
        if job.get("status") not in {"saved", "prepared"}:
            return f"The job is marked {job.get('status')}, so nothing more was prepared."
        return ""

    def _web_choice(self, config):
        """Steps that search the web run on the chosen AI when it can; otherwise the app picks one that can."""
        engine = self.runner.gateway.providers.get(config["provider"])
        if engine is not None and "web" in engine.capabilities:
            return config["provider"], config["model"]
        return None, None

    def _team(self, config):
        from backend.ai import _default_model, route_options, usage_recorder
        from backend.ai.agents.graph import AgentTeam
        from backend.ai.persona import persona_for

        provider, model = config["provider"], config["model"]
        # Reading and classifying runs on the provider's light model; writing on the chosen one.
        # Auto picks each plan's writing and reading model itself.
        cheap = model if provider in ("codex", "kimi_cli", "antigravity_cli", "auto") else _default_model(provider, "cheap")
        return AgentTeam(self.w.root, {"strong": (provider, model), "cheap": (provider, cheap)}, usage_recorder(self.s),
                         persona=persona_for(self.w.root), route=route_options(self.s, "daily_search"))

    def run_step(self, step: str, job_id: str, config: dict) -> dict:
        """One helper (any of STEP_IDS) for one saved job; the chat and Resume Studio can call it too."""
        from backend import telemetry

        if step not in STEP:
            raise ValueError("Unknown helper: " + step)
        issue = self._preparation_issue(job_id)
        if step != "posting" and issue:
            raise JobStopped(issue)
        with telemetry.bind(profile_root=self.w.root):
            with telemetry.span(f"pipeline.step {step}", **{"career.node": step, "career.job_id": job_id}):
                return getattr(self, "_" + step)(job_id, config)

    def _agent(self, kind, job_id, provider, model, preset="default", count=None, timeout_minutes=45) -> dict:
        queued = self.runner.enqueue(kind, job_id, provider, model, preset, count=count)
        deadline = time.monotonic() + timeout_minutes * 60
        while time.monotonic() < deadline:
            with self.w.connect() as db:
                row = db.execute("SELECT id, state, result, error FROM agent_runs WHERE id=?", (queued["id"],)).fetchone()
            if row and row["state"] == "completed":
                return {"id": row["id"], "result": json.loads(row["result"] or "{}")}
            if row and row["state"] == "failed":
                raise ValueError(row["error"] or "The step failed without a reason.")
            time.sleep(self.poll)
        raise ValueError(f"This step did not finish within {timeout_minutes} minutes.")

    def _posting(self, job_id, config) -> dict:
        from backend.job_quality import JobQualityService

        if self.w.get_job(job_id).get("record_source") == "gmail":
            return {"note": "This record has no public posting to check.", "skipped": True}
        checked = JobQualityService(self.s).verify_posting(job_id)
        if checked.get("excluded"):
            raise JobStopped("The posting now refuses sponsorship, so it moved to Excluded roles "
                             "and nothing more was prepared.")
        if checked["state"] == "expired":
            raise JobStopped("The posting has closed (" + " ".join(checked["evidence"])[:200]
                             + "), so nothing more was prepared.")
        if checked["state"] == "needs_review":
            return {"note": "The site blocked the automatic check; the other steps still run. "
                            "Open the link to confirm it is open before applying.", "posting": "needs_review"}
        return {"note": "Still open.", "posting": "active"}

    def _research(self, job_id, config) -> dict:
        from backend.services import fit

        provider, model = self._web_choice(config)
        self._agent("research", job_id, provider, model)
        # The requirement check: each must-have met, partly met or missing, from registered evidence.
        # AI on a free plan when one is free, else the rules path; never a paid key.
        try:
            analysis = fit.for_job(self.s, job_id)
            how = "AI" if analysis["method"] == "ai" else "rules"
            return {"note": f"Research saved with this job. Fit {analysis['score']}/100 ({how} check): "
                            + (fit.brief(analysis) or "no must-haves recognised") + ".",
                    "fit": analysis["score"]}
        except Exception as exc:  # noqa: BLE001 - the research itself is done; the fit can be rechecked later
            return {"note": "Research saved with this job. The requirement check could not run: " + str(exc)[:200]}

    def _tailor(self, job_id, config) -> dict:
        result = self.studio.tailor(job_id, self._team(config))
        items = result.get("items") or {}
        verified, predicted = items.get("verified", 0), items.get("predicted", 0)
        note = f"{verified} verified items from your registry"
        if predicted:
            note += f" and {predicted} predicted item{'s' if predicted != 1 else ''} to keep or remove in Assurance"
        dropped = result.get("dropped") or []
        return {"note": note + (f"; {len(dropped)} unusable suggestion{'s' if len(dropped) != 1 else ''} left out" if dropped else "") + "."}

    def _study_plan(self, job_id, config) -> dict:
        provider, model = self._web_choice(config)
        self._agent("study_plan", job_id, provider, model)
        return {"note": "Saved to study-plan.md"}

    def _pdf(self, job_id, config) -> dict:
        from backend.resume_contract import contract_for

        contract = contract_for(self.w.root)
        draft = self.studio.get(job_id)
        preview = draft.get("preview") or {}
        if preview.get("current") and preview.get("revision") == draft["revision"] and preview.get("page_count") == contract.pages:
            return {"note": f"{contract.describe_pages().capitalize()}. The PDF made while tailoring is current.", "quick": True}
        fitted = self.studio.fit(job_id, draft["revision"])
        pages = (fitted.get("preview") or {}).get("page_count")
        if pages != contract.pages:
            raise ValueError(f"The PDF came out at {pages} pages. Open Resume Studio and use Fit to one page.")
        return {"note": f"{contract.describe_pages().capitalize()} PDF ready"}

    def _review(self, job_id, config) -> dict:
        draft = self.studio.get(job_id)
        preview = draft.get("preview") or {}
        if not preview.get("current") or preview.get("revision") != draft["revision"]:
            return {"note": "No current PDF to review: the resume steps did not finish.", "skipped": True}
        # A fresh AI with the PDF text and the posting only (services/agents.py resume_match); no web.
        record = self._agent("resume_match", job_id, config["provider"], config["model"])
        result = record.get("result")
        review = result.get("review") if isinstance(result, dict) else None
        review = review if isinstance(review, dict) else {}
        summary = " ".join(str(review.get("summary") or "").split())
        verdict = review.get("verdict")
        issues = review.get("issues")
        if (not isinstance(verdict, str) or verdict not in {"pass", "review", "blocked"}
                or not isinstance(issues, list) or any(not isinstance(issue, str) or not issue.strip() for issue in issues)
                or verdict != "pass" and not issues):
            verdict, issues = "review", ["Run a new independent review with a recorded verdict."]
        elif verdict == "pass" and issues:
            verdict = "review"
        label = {"pass": "Independent check passed", "review": "Independent review needs your attention",
                 "blocked": "Independent review found a blocking issue"}[verdict]
        return {"note": label + (": " + summary[:300] if summary else "."), "review_verdict": verdict, "issues": issues}

    def _ready(self, job_id, config) -> dict:
        from backend.services import readiness

        try:
            self.studio.score(job_id)  # the deterministic assessment of the current PDF; a no-op when it has one
        except ValueError:
            pass  # no current PDF: the check below says so
        result = readiness.check(self.s, self.studio, job_id)
        head = result["label"] + (f" · readiness {result['score']}/100" if result["score"] is not None else "")
        return {"note": head + (". Next: " + result["next"][0] if result["next"] else "."),
                "verdict": result["verdict"], "score": result["score"], "next": result["next"][:3]}
