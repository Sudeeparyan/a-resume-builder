#!/usr/bin/env python3
"""
pack_skill.py — bundle this workspace into a portable, standalone resume-tailor skill.

  python3 system/scripts/pack_skill.py --name jane-resume-tailor --out dist/

Produces dist/<name>/ containing SKILL.md, references/ and assets/ with every path rewritten
so the skill needs nothing outside its own folder. Install it in any Claude session (drop it in
.claude/skills/ or upload it) and the tailoring works without this repo.

The workspace stays the source of truth: re-run this after updating system/profile/ to refresh the
bundle. Stdlib only.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

# scripts live at <workspace>/system/scripts/, so the workspace root is three levels up
ROOT = Path(__file__).resolve().parents[2]

# source in the repo -> destination inside the packed skill
COPY_MAP = {
    "system/profile/master-profile.md": "references/master-profile.md",
    "system/profile/positioning.md": "references/positioning.md",
    "system/profile/skills-matrix.md": "references/skills-matrix.md",
    "system/profile/interview-stories.md": "references/interview-stories.md",
    ".claude/skills/resume-tailor/references/tailoring-playbook.md": "references/tailoring-playbook.md",
    ".claude/skills/resume-tailor/references/ats-rules.md": "references/ats-rules.md",
    ".claude/skills/resume-tailor/references/output-formats.md": "references/output-formats.md",
    "system/templates/latex/resume-track-a.tex": "assets/resume-track-a.tex",
    "system/templates/latex/resume-track-b.tex": "assets/resume-track-b.tex",
    "system/templates/latex/cover-letter.tex": "assets/cover-letter.tex",
    "system/templates/markdown/resume.md": "assets/resume.md",
    "system/modes/_shared.md": "references/system-rules.md",
    "system/modes/_profile.md": "references/personal-overrides.md",
}

# path rewrites applied to every packed file, longest first
REWRITES = [
    ("system/profile/master-profile.md", "references/master-profile.md"),
    ("system/profile/positioning.md", "references/positioning.md"),
    ("system/profile/skills-matrix.md", "references/skills-matrix.md"),
    ("system/profile/interview-stories.md", "references/interview-stories.md"),
    (".claude/skills/resume-tailor/references/", "references/"),
    ("system/templates/latex/resume-track-a.tex", "assets/resume-track-a.tex"),
    ("system/templates/latex/resume-track-b.tex", "assets/resume-track-b.tex"),
    ("system/templates/latex/cover-letter.tex", "assets/cover-letter.tex"),
    ("system/templates/markdown/resume.md", "assets/resume.md"),
    ("system/modes/_shared.md", "references/system-rules.md"),
    ("system/modes/_profile.md", "references/personal-overrides.md"),
    ("system/config/profile.yml", "references/positioning.md"),   # config facts live in positioning
]

TOKEN = re.compile(r"\{\{[A-Z][A-Z_0-9]*\}\}")


def rewrite(text: str) -> str:
    for old, new in sorted(REWRITES, key=lambda p: -len(p[0])):
        text = text.replace(old, new)
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True, help="skill folder name, e.g. jane-resume-tailor")
    ap.add_argument("--out", default="dist", help="output directory (default: dist)")
    ap.add_argument("--force", action="store_true", help="pack even if placeholders remain")
    args = ap.parse_args()

    # Refuse to ship a skill full of unfilled placeholders — it would produce fabricated resumes.
    unfilled = {}
    for src in COPY_MAP:
        p = ROOT / src
        if p.exists():
            found = TOKEN.findall(p.read_text(encoding="utf-8"))
            if found:
                unfilled[src] = len(found)
    if unfilled and not args.force:
        print("Refusing to pack: these files still contain unfilled placeholders.\n", file=sys.stderr)
        for k, v in unfilled.items():
            print(f"  {k}: {v}", file=sys.stderr)
        print("\nRun the profile-intake skill first, or pass --force to pack anyway.", file=sys.stderr)
        return 1

    dest = Path(args.out)
    if not dest.is_absolute():
        dest = ROOT / dest
    dest = dest / args.name
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "references").mkdir(parents=True)
    (dest / "assets").mkdir(parents=True)

    packed = []
    for src, rel in COPY_MAP.items():
        p = ROOT / src
        if not p.exists():
            print(f"  skipped (missing): {src}")
            continue
        text = rewrite(p.read_text(encoding="utf-8"))
        (dest / rel).write_text(text, encoding="utf-8")
        packed.append(rel)

    skill_src = ROOT / ".claude/skills/resume-tailor/SKILL.md"
    skill = rewrite(skill_src.read_text(encoding="utf-8"))
    skill = skill.replace("name: resume-tailor", f"name: {args.name}")
    skill += (
        "\n\n## Packed skill note\n\n"
        "This is a self-contained bundle: every file referenced above lives inside this skill "
        "folder, so it works in any session without the workspace it was packed from. "
        "Regenerate it with `system/scripts/pack_skill.py` after updating the profile — the workspace "
        "remains the source of truth.\n")
    (dest / "SKILL.md").write_text(skill, encoding="utf-8")
    packed.append("SKILL.md")

    print(f"Packed {len(packed)} file(s) into {dest}:")
    for f in sorted(packed):
        print(f"  {f}")
    print("\nInstall by copying that folder into .claude/skills/ in any project, "
          "or uploading it as a skill.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
