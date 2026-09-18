#!/bin/bash
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "$(dirname "$0")/backend"
if [ ! -x .venv/bin/python ]; then
  python3.12 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
exec .venv/bin/python ../../daily-job-search/with_resume_runtime.py .venv/bin/python run.py "$@"
