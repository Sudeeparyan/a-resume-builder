"""
The bridge to system/scripts/*.py.

Those scripts are standalone, stdlib-only, and have no package structure: each
computes ROOT = parents[2] from its own location, so they must be imported in
place rather than copied. Other workflows (/hunt, the skills) depend on them
exactly as they are, so NOTHING here edits them -- three known defects are
patched at the call boundary instead:

  1. track.TODAY is bound at import time. A server process that lives for days
     would compute cooldowns against a stale date, silently un-suppressing a
     rejected company. refresh_today() rebinds it before every wrapped call.
  2. sponsor_check.load_config() calls die() -> sys.exit(2) when the YAML is
     missing, which would kill the web server. We pre-check and raise instead.
  3. sponsor_check.lookup_history() linear-scans an 83,624-row / 5.9 MB CSV on
     every call. services/sponsor_index.py builds a SQLite index; the raw scan
     stays as the fallback when the index has not been built yet.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

from . import paths


class LegacyUnavailable(RuntimeError):
    """A required part of the workspace is missing. Carries a plain-English fix."""


def _load(alias: str, filename: str):
    """
    Load one script under a namespaced module name.

    Deliberately NOT sys.path.insert(0, SCRIPTS): that would put the workspace's
    track.py ahead of every other module named 'track' on the path, silently
    shadowing a dependency. Namespacing under 'annie_legacy.' keeps them
    isolated while still executing the file in place, so each script's own
    ROOT = parents[2] still resolves correctly.
    """
    import importlib.util

    mod_name = f"annie_legacy.{alias}"
    if mod_name in sys.modules:
        return sys.modules[mod_name]

    path = paths.SCRIPTS / filename
    if not path.exists():
        raise LegacyUnavailable(
            f"{filename} is missing from system/scripts/. The workspace is incomplete."
        )
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise LegacyUnavailable(f"Could not load {filename}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001
        sys.modules.pop(mod_name, None)
        raise LegacyUnavailable(f"{filename} failed to load: {exc}") from exc
    return module


# A parent package so the namespaced children resolve cleanly.
if "annie_legacy" not in sys.modules:
    import types

    sys.modules["annie_legacy"] = types.ModuleType("annie_legacy")

ats_check = _load("ats_check", "ats_check.py")
build_pdf = _load("build_pdf", "build_pdf.py")
sponsor_check = _load("sponsor_check", "sponsor_check.py")
track = _load("track", "track.py")
verify_job_url = _load("verify_job_url", "verify_job_url.py")

TRACK_FIELDS: list[str] = list(track.FIELDS)
OPEN_STATUSES: set[str] = set(track.OPEN_STATUSES)
CLOSED_STATUSES: set[str] = set(track.CLOSED_STATUSES)
GHOST_AFTER_DAYS: int = track.GHOST_AFTER_DAYS
REJECT_COOLDOWN_DAYS: int = track.REJECT_COOLDOWN_DAYS
GHOST_COOLDOWN_DAYS: int = track.GHOST_COOLDOWN_DAYS
MIN_FILL_CHARS: int = getattr(build_pdf, "MIN_FILL_CHARS", 3300)


# --------------------------------------------------------------------------
# defect 1 -- track.TODAY is frozen at import
# --------------------------------------------------------------------------
def refresh_today() -> date:
    today = date.today()
    track.TODAY = today
    return today


# --------------------------------------------------------------------------
# defect 2 -- load_config() exits the process on a missing file
# --------------------------------------------------------------------------
_cfg_cache: dict[str, Any] | None = None
_cfg_mtime: float | None = None


def sponsorship_config(force: bool = False) -> dict:
    """Cached sponsorship.yml, reloaded when the file changes on disk."""
    global _cfg_cache, _cfg_mtime
    p = paths.SPONSORSHIP_YML
    if not p.exists():
        raise LegacyUnavailable(
            f"The sponsorship rules are missing ({p}). Without them no job can be "
            "screened, so the scan cannot run."
        )
    mtime = p.stat().st_mtime
    if force or _cfg_cache is None or mtime != _cfg_mtime:
        try:
            _cfg_cache = sponsor_check.load_config(p)
        except SystemExit as exc:  # die() inside the script
            raise LegacyUnavailable(f"Could not read the sponsorship rules ({p}).") from exc
        _cfg_mtime = mtime
    return _cfg_cache


def screen_jd(jd_text: str) -> dict:
    """
    The hard sponsorship gate. Returns the script's dict verbatim:
    {verdict, reason, reason_label, pattern, sentence, tier, everify, evidence}

    verdict is EXCLUDED or KEEP. Silence about sponsorship is a KEEP -- that is
    most postings and the largest bucket. Only an explicit refusal, or a
    citizenship/clearance/ITAR requirement, excludes.
    """
    return sponsor_check.screen(jd_text or "", sponsorship_config())


def cap_exempt(company: str, domain: str = "") -> tuple[bool, str]:
    return sponsor_check.is_cap_exempt(company or "", sponsorship_config(), domain or "")


def normalize_company(name: str) -> str:
    return sponsor_check.normalize(name or "")


# --------------------------------------------------------------------------
# tracker
# --------------------------------------------------------------------------
def load_applications() -> list[dict]:
    refresh_today()
    return track.load()


def save_applications(rows: list[dict]) -> None:
    track.save(rows)


def exclusions() -> tuple[set, set, list]:
    """(company+role pairs never to surface, companies in cooldown, reasons)"""
    refresh_today()
    return track.exclusion_sets(track.load())


def next_app_id(rows: list[dict] | None = None) -> str:
    return track.next_id(rows if rows is not None else track.load())


# --------------------------------------------------------------------------
# ATS
# --------------------------------------------------------------------------
def jd_keywords(jd_text: str, top: int = 25) -> list[tuple[str, int]]:
    return ats_check.jd_keywords(jd_text or "", top)


def strip_latex(text: str) -> str:
    return ats_check.strip_latex(text or "")


def ats_score(resume_text: str, jd_text: str, top: int = 25, is_latex: bool = True) -> dict:
    """
    Keyword coverage, using the same maths as ats_check.py:
        score = 100 * (covered + 0.5 * thin) / len(rows)
    'thin' means the term appears once where the JD wants it repeated.
    """
    body = strip_latex(resume_text) if is_latex else (resume_text or "")
    resume_norm = ats_check.normalise(body)
    rows = ats_check.jd_keywords(jd_text or "", top)
    if not rows:
        return {"score": 0, "rows": [], "covered": 0, "thin": 0, "missing": []}

    out, covered, thin = [], 0, 0
    for term, weight in rows:
        count = ats_check.count_in(resume_norm, term)
        if count >= 2:
            covered += 1
        elif count == 1:
            thin += 1
        out.append({"term": term, "weight": weight, "count": count})

    return {
        "score": round(100 * (covered + 0.5 * thin) / len(rows)),
        "rows": out,
        "covered": covered,
        "thin": thin,
        "missing": [r["term"] for r in out if r["count"] == 0],
    }


# --------------------------------------------------------------------------
# links
# --------------------------------------------------------------------------
def check_url(url: str) -> dict:
    """ACTIVE | EXPIRED | BROKEN | NEEDS_CHECK. Never raises."""
    return verify_job_url.check(url)


# --------------------------------------------------------------------------
# LaTeX
# --------------------------------------------------------------------------
def check_tex_source(tex: Path) -> list[str]:
    """Blocking problems: {{TOKENS}}, [FILL IN ...], brace imbalance, double hyperref."""
    return build_pdf.check_source(Path(tex))


def count_pdf_pages(pdf: Path) -> int:
    return build_pdf.count_pages(Path(pdf))


def pdf_text_chars(pdf: Path) -> int:
    """How much extractable text the PDF has. Low means an under-filled page."""
    return build_pdf.extract_text_chars(Path(pdf))
