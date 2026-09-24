"""Where everything lives.

One module answers "where is X", so a directory move is a change here rather
than in every caller. APP_ROOT is the career-dashboard folder regardless of how
deep the importing module sits.
"""

from __future__ import annotations

from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]

BACKEND = APP_ROOT / "backend"
FRONTEND = APP_ROOT / "frontend"
DATA = APP_ROOT / "data"
TESTS = APP_ROOT / "tests"
DOCS = APP_ROOT / "docs"

SCRIPTS = BACKEND / "scripts"
SERVICES = BACKEND / "services"
WORKFLOWS = BACKEND / "workflows"

CONFIG = DATA / "config"
CONTEXT = DATA / "context"
TEMPLATES = DATA / "templates"
OUTPUT = DATA / "output"

# Repository root, one level above the app: daily-job-search/ and backup/ sit there.
REPO_ROOT = APP_ROOT.parent

# Every profile after Annie lives in its own folder here (profiles/<id>/data/...).
# Annie, the backup profile, keeps the app's own data/ folder.
PROFILES = APP_ROOT / "profiles"
# Country packs: location terms, work-authorization gate, paper and spelling per country.
COUNTRIES = BACKEND / "countries"

# The default local time zone when a profile names none: "today" for daily targets,
# mail dates and search runs. Annie is in Fayetteville, AR (US Central). A profile's
# own `candidate.timezone` in profile.yml wins (Workspace.timezone).
TIMEZONE = "America/Chicago"


def app_root_for(root) -> Path:
    """The folder holding code and secrets for a workspace rooted at `root`.

    Annie's workspace (and every test copy) is the app itself: it has a backend/
    folder. A profile folder holds only data, so its code, .env and keys are the app's.
    """
    root = Path(root).resolve()
    return root if (root / "backend").is_dir() else APP_ROOT


def secrets_root_for(root) -> Path:
    """Where the AI keys (.env, keys.txt) for a workspace are read.

    A profile folder (under profiles/) uses the app's keys: they belong to the machine,
    not to a person. Any other root (Annie's, or a test's temporary folder) keeps its own.
    """
    root = Path(root).resolve()
    try:
        root.relative_to(PROFILES.resolve())
    except ValueError:
        return root
    return APP_ROOT

APP_ID = "annie-career-workspace"
APP_TITLE = "Career Workspace"
# Loopback port for run.py and the Vite dev proxy. 8000 belongs to another
# dashboard on this Mac; the launcher must never open a browser on someone
# else's app, so Annie's port is distinct and run.py checks the health id.
DEFAULT_PORT = 8010
