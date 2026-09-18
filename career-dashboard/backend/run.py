#!/usr/bin/env python3
"""Start the local dashboard.

From this folder, with the venv active:  python run.py
The React client is rebuilt first when its sources changed.

The port defaults to paths.DEFAULT_PORT (8010). Another career dashboard on
this Mac listens on 8000, so before anything opens a browser tab the launcher
asks the port who is there: it only ever opens Annie's own app, and it refuses
plainly when the port belongs to something else.
"""
import argparse
import importlib.util
import json
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

# Make ``backend`` importable however this file is launched, then let paths.py
# answer everything else.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.paths import APP_ID, APP_ROOT, APP_TITLE, DEFAULT_PORT, SCRIPTS  # noqa: E402

sys.path.insert(0, str(SCRIPTS))


def health(url, timeout=1.0):
    """The /api/health document of whatever answers at ``url``, or None."""
    try:
        with urllib.request.urlopen(url + "/api/health", timeout=timeout) as response:
            document = json.load(response)
    except (OSError, ValueError):
        return None
    return document if isinstance(document, dict) else None


def is_ours(document):
    return bool(document) and document.get("app") == APP_ID and document.get("root") == str(APP_ROOT)


def port_state(port, host="127.0.0.1"):
    """'ours' | 'free' | 'other' — what is on the port right now.

    Returns a (state, detail) pair; ``detail`` names the other occupant so the
    message the user sees says whose app it is instead of a bare bind error.
    """
    document = health(f"http://{host}:{port}")
    if is_ours(document):
        return "ours", ""
    if document:
        return "other", f"{document.get('app') or 'another dashboard'} at {document.get('root') or '?'}"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        # Same option uvicorn binds with, so a just-stopped server's TIME_WAIT
        # sockets do not read as an occupant while a live listener still does.
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return "other", "another program (no dashboard health endpoint)"
    return "free", ""


def open_when_ready(url, deadline_seconds=30.0):
    """Open a browser tab only once ``url`` answers as this app."""
    stop = time.monotonic() + deadline_seconds
    while time.monotonic() < stop:
        if is_ours(health(url)):
            webbrowser.open(url)
            return True
        time.sleep(0.4)
    return False


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port from 1024 to 65535")
    if importlib.util.find_spec("uvicorn") is None:
        raise SystemExit(
            "Install dependencies first: python -m pip install -r requirements.txt"
        )
    url = f"http://127.0.0.1:{args.port}"
    state, detail = port_state(args.port)
    if state == "ours":
        print(f"Dashboard already running: {url}", flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        return
    if state == "other":
        raise SystemExit(
            f"Port {args.port} is already used by {detail}.\n"
            f"That is not {APP_TITLE}, so no browser tab was opened.\n"
            f"Start this app on a free port instead:  python run.py --port {args.port + 1}"
        )

    from build_frontend import build

    build()
    import uvicorn
    from backend.dashboard.app import create_app

    print(f"{APP_TITLE}: {url}", flush=True)
    if not args.no_browser:
        opener = threading.Thread(target=open_when_ready, args=(url,), daemon=True)
        opener.start()
    uvicorn.run(create_app(schedule=True), host="127.0.0.1", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
