"""
The honesty wall, end to end through the running API.

Plants four lies a careless model might write and asserts the server refuses to
produce a downloadable PDF. This is the single most important behaviour in the
whole system: LaTeX compiles fine, and the build is blocked anyway.

Run the server first, then: python dashboard/tests/probe_honesty.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import paths  # noqa: E402

BASE = "http://127.0.0.1:8000"
FOLDER = "Annie_Manoharan_USC_01"

LIES = [
    r"\resumeItem{Cut inference latency by 47.3\% using Kubernetes and Snowflake}",
    r"\resumeItem{Data engineer with 8 years of professional experience}",
    r"\resumeItem{Responsible for the data platform, published in ICCV 2025}",
    r"\resumeItem{Processed [FILL IN: records per day] records}",
]


def main() -> int:
    tex = paths.read_text(paths.OUTPUT / FOLDER / "resume.tex")
    anchor = "\\section{Technical Skills}"
    assert anchor in tex, "anchor not found in the real resume"
    poisoned = tex.replace(anchor, "\n".join(LIES) + "\n" + anchor, 1)
    assert poisoned != tex

    with httpx.Client(timeout=120) as c:
        clean = c.post(
            f"{BASE}/api/resumes/{FOLDER}/compile", json={"tex": tex, "mode": "ship"}
        ).json()
        print("CLEAN resume")
        print(f"  ship ok        : {clean['ok']}   (want True)")
        print(f"  pages          : {clean['pages']}")
        print(f"  blockers       : {clean['guards']['blocker_count']}")

        bad = c.post(
            f"{BASE}/api/resumes/{FOLDER}/compile", json={"tex": poisoned, "mode": "ship"}
        ).json()

    print("\nPOISONED resume")
    print(f"  ship ok        : {bad['ok']}   (want False)")
    print(f"  latex pages    : {bad['pages']}   (LaTeX itself was happy)")
    print(f"  blockers       : {bad['guards']['blocker_count']}")
    print("\n  what was caught:")
    for v in bad["guards"]["violations"]:
        if v["severity"] == "blocker":
            print(f"    [{v['kind']:20s}] {str(v['token'])[:24]:24s} line {v['line']}")

    kinds = {v["kind"] for v in bad["guards"]["violations"] if v["severity"] == "blocker"}
    expected = {
        "FABRICATION_NUMBER",   # 47.3 is not in her files
        "HONESTY_WALL",         # Kubernetes / Snowflake are honest gaps
        "BLOCKED_CLAIM",        # years total and the publication
        "FILL_IN_LEFT",         # an unanswered marker must never ship
    }
    missing = expected - kinds
    ok = clean["ok"] and not bad["ok"] and not missing

    print("\n" + "=" * 60)
    if missing:
        print(f"FAIL — these checks did not fire: {sorted(missing)}")
    elif bad["ok"]:
        print("FAIL — a fabricated resume was allowed to ship")
    elif not clean["ok"]:
        print("FAIL — the real resume was wrongly blocked")
    else:
        print("PASS — fabrications blocked, the honest resume still ships")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
