#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/career-dashboard"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
PY=backend/.venv/bin/python
"$PY" ../daily-job-search/with_resume_runtime.py "$PY" -m pytest tests -q
"$PY" backend/scripts/validate_workspace.py
"$PY" backend/scripts/check_layout.py

"$PY" backend/scripts/build_frontend.py
(cd frontend && npm test)
