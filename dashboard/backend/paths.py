"""
Every path in the dashboard resolves from here.

The workspace layout is fixed by CLAUDE.md and must not be second-guessed:
context/ is the user's, output/ is generated, system/ is the machinery.
This module is the only place that knows where the repo root is.
"""

from __future__ import annotations

import os
from pathlib import Path


def _resolve_root() -> Path:
    """
    Where the workspace lives.

    By default it is the repo this file sits in. CAREER_OPS_ROOT points
    somewhere else entirely, which is what makes one copy of the code usable by
    more than one person: each keeps their own workspace folder -- their
    context/, their output/, their tracker -- and nobody's private profile has
    to live in the repository.

    legacy.py loads system/scripts/*.py from paths.SCRIPTS, and those scripts
    compute their own root the same way relative to where they were found, so
    an override stays consistent all the way down.
    """
    env = os.environ.get("CAREER_OPS_ROOT", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "context").exists() or (p / "system").exists():
            return p
    # dashboard/backend/paths.py -> backend -> dashboard -> <repo root>
    return Path(__file__).resolve().parents[2]


ROOT = _resolve_root()

CONTEXT = ROOT / "context"
CONTEXT_FILES = CONTEXT / "files"
QUESTIONS = CONTEXT / "QUESTIONS-FOR-YOU.md"

SYSTEM = ROOT / "system"
SCRIPTS = SYSTEM / "scripts"
CONFIG = SYSTEM / "config"
DATA = SYSTEM / "data"
MODES = SYSTEM / "modes"
PROFILE = SYSTEM / "profile"
TEMPLATES = SYSTEM / "templates"
LATEX_TEMPLATES = TEMPLATES / "latex"
BIN = SYSTEM / "bin"

OUTPUT = ROOT / "output"
SUMMARY = OUTPUT / "SUMMARY.md"

APPLICATIONS_TSV = DATA / "applications.tsv"
SIGNATURE_PROJECTS = DATA / "signature-projects.md"
APPLIED_COMPANIES = DATA / "applied-companies.md"
SCAN_HISTORY = DATA / "scan-history.tsv"
COMPANY_NOTES = DATA / "company-notes.md"
SPONSORS_CSV = DATA / "sponsors-uscis.csv"

SPONSORSHIP_YML = CONFIG / "sponsorship.yml"
PROFILE_YML = CONFIG / "profile.yml"
PORTALS_YML = CONFIG / "portals.yml"
REGIONS_YML = CONFIG / "regions.yml"

# dashboard's own territory — everything we create lives under here
DASHBOARD = ROOT / "dashboard"
DB_DIR = DASHBOARD / "data"
DB_PATH = DB_DIR / "dashboard.db"
ENV_FILE = DASHBOARD / ".env"
STATUS_MD = DASHBOARD / "STATUS.md"
FRONTEND_DIST = DASHBOARD / "frontend" / "dist"
GOLDEN_DIR = DASHBOARD / "backend" / "evals" / "golden"
TMP = DB_DIR / "tmp"


def tectonic() -> Path | None:
    """The LaTeX engine. Gitignored, so it may genuinely be absent."""
    for name in ("tectonic.exe", "tectonic"):
        p = BIN / name
        if p.exists():
            return p
    return None


def ensure_dirs() -> None:
    for d in (DB_DIR, TMP, OUTPUT, GOLDEN_DIR):
        d.mkdir(parents=True, exist_ok=True)


def read_text(path: Path, default: str = "") -> str:
    """UTF-8 everywhere. Windows default encoding corrupts the LaTeX and the em-dashes."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return default


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
