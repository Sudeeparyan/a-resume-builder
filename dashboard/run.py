#!/usr/bin/env python3
"""
Start the dashboard.

    python dashboard/run.py

One process, one port, both tabs. Builds the frontend on first run if npm is
available; falls back to an API-only mode with a clear message if it is not.
"""

from __future__ import annotations

import subprocess
import sys
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from backend import paths, settings  # noqa: E402


def npm() -> str | None:
    import shutil
    for name in ("npm.cmd", "npm"):
        p = shutil.which(name)
        if p:
            return p
    return None


def build_frontend() -> bool:
    fe = HERE / "frontend"
    if not (fe / "package.json").exists():
        return False
    exe = npm()
    if not exe:
        print("! npm was not found, so the web page cannot be built.")
        print("  The API will still run at /api, and /docs lists every endpoint.")
        return False
    if not (fe / "node_modules").exists():
        print("Installing the web page's dependencies (once, about a minute)...")
        if subprocess.run([exe, "install"], cwd=fe).returncode != 0:
            return False
    print("Building the web page...")
    return subprocess.run([exe, "run", "build"], cwd=fe).returncode == 0


def main() -> int:
    import uvicorn

    paths.ensure_dirs()
    if not paths.FRONTEND_DIST.exists():
        build_frontend()

    cfg = settings.get_settings()
    url = f"http://{cfg.host}:{cfg.port}"
    print("\n" + "=" * 62)
    print("  Your dashboard is starting")
    print(f"  Open: {url}")
    if not cfg.has_key():
        print("\n  No API key yet — that is fine. Job finding, the sponsorship")
        print("  check, link checking and PDF building all work without one.")
        print("  Add a key in Settings to switch on research and tailoring.")
    print("=" * 62 + "\n")

    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001
        pass

    uvicorn.run("backend.main:app", host=cfg.host, port=cfg.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
