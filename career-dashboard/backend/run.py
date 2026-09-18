#!/usr/bin/env python3
"""Start the local dashboard.

From this folder, with the venv active:  python run.py
The React client is rebuilt first when its sources changed.
"""
import argparse
import importlib.util
import json
import sys
import threading
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

# Make ``backend`` importable however this file is launched, then let paths.py
# answer everything else.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.paths import APP_ID, APP_ROOT, APP_TITLE, SCRIPTS  # noqa: E402

sys.path.insert(0, str(SCRIPTS))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port from 1024 to 65535")
    if importlib.util.find_spec("uvicorn") is None:
        raise SystemExit(
            "Install dependencies first: python -m pip install -r requirements.txt"
        )
    from build_frontend import build

    build()
    import uvicorn
    from backend.dashboard.app import create_app

    url = f"http://127.0.0.1:{args.port}"
    try:
        with urllib.request.urlopen(url + "/api/health", timeout=1) as response:
            running = json.load(response)
        if running.get("app") == APP_ID and running.get(
            "root"
        ) == str(APP_ROOT):
            print(f"Dashboard already running: {url}", flush=True)
            if not args.no_browser:
                webbrowser.open(url)
            return
    except (OSError, ValueError):
        pass
    print(f"{APP_TITLE}: {url}", flush=True)
    if not args.no_browser:
        timer = threading.Timer(1.2, lambda: webbrowser.open(url))
        timer.daemon = True
        timer.start()
    uvicorn.run(create_app(schedule=True), host="127.0.0.1", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
