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

# The candidate's local time zone: "today" for daily targets, mail dates and search runs.
# Annie is in Fayetteville, AR (US Central). Change here, nowhere else.
TIMEZONE = "America/Chicago"

APP_ID = "annie-career-workspace"
APP_TITLE = "Annie Career Workspace"
