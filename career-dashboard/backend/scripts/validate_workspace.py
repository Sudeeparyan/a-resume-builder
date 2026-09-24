#!/usr/bin/env python3
"""Validate Annie's profile, sponsorship gate, agent guardrails, workflow paths, and base resume.

Nothing candidate-specific is pinned here: names, dates, employers, page count and
paper come from data/config/profile.yml and data/context/evidence.yml through
backend/resume_contract.py, so a registry update never needs a validator edit.
"""

from __future__ import annotations

import ast
import csv
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
from backend.resume_contract import load_contract  # noqa: E402

CONTRACT = load_contract()
ERRORS: list[str] = []
WARNINGS: list[str] = []

REQUIRED_FILES = (
    "AGENTS.md",
    "README.md",
    "DATA_CONTRACT.md",
    "data/config/profile.yml",
    "data/config/portals.yml",
    "data/config/sponsorship.yml",
    "data/config/regions.yml",
    "data/context/01-basics.md",
    "data/context/02-education.md",
    "data/context/03-experience.md",
    "data/context/04-projects.md",
    "data/context/05-skills.md",
    "data/context/06-achievements.md",
    "data/context/07-preferences.md",
    "data/context/08-voice.md",
    "data/context/09-anything-else.md",
    "data/context/QUESTIONS-FOR-YOU.md",
    "data/context/PROFILE.md",
    "data/context/PROFILE-NOTES.md",
    "data/context/evidence.yml",
    "data/sponsors/sponsors-uscis.csv",
    "data/signature-projects.md",
    "data/templates/resume-base.tex",
    "data/templates/batch.example.yml",
    "data/templates/evidence-map.example.yml",
    "data/output/README.md",
    "backend/workflows/modes/_shared.md",
    "backend/workflows/modes/_profile.md",
    "backend/workflows/modes/resume.md",
    "backend/workflows/modes/quality.md",
    "backend/workflows/modes/batch-resumes.md",
    "backend/workflows/modes/upskill.md",
    "backend/workflows/agents/job-discovery.md",
    "backend/workflows/agents/study-planner.md",
)
# The skills every AI app reads (Claude Code, Codex, Kimi Code, ...), at the repo root beside the
# one AGENTS.md; relative to REPO_ROOT.
SKILLS_DIR = ".agents/skills"
REQUIRED_SKILLS = ("hunt", "job-hunter", "resume-tailor", "profile-intake", "interview-prep", "verify-job-url")

# The previous edition of this app belonged to another candidate. None of his
# identity, employers, clients or Irish immigration terms may reach Annie's active
# content. Split so this file never matches itself.
PREVIOUS_EDITION = tuple(
    "".join(parts)
    for parts in (
        ("Chetan ", "Babu"),
        ("chetan", "babu07"),
        ("Info", "cepts"),
        ("Astra", "Zeneca"),
        ("Nielsen", "IQ"),
        ("Hindustan ", "Unilever"),
        ("Munster ", "Technological"),
        ("SRM ", "Institute"),
        ("Europe/", "Dublin"),
        ("Stamp ", "1G"),
        ("Critical Skills ", "Employment Permit"),
    )
)
# Other profiles are real now (backend/profiles.py): the country packs, the document
# intake and their tests name Irish immigration terms, and a test profile's own
# university, on purpose. Those files only; Annie's data, guides and agents stay clean.
PREVIOUS_EDITION_ALLOWED = (
    "backend/countries/",
    "backend/services/intake/",
    "backend/ai/agents/schemas.py",
    "frontend/src/profiles.tsx",
    "frontend/src/features/Onboarding.tsx",
    "frontend/src/features/OnboardingChat.tsx",
    "tests/fixtures/intake_draft.py",
    "tests/test_intake_build.py",
    "tests/test_profiles.py",
    "tests/test_setup_chat.py",
)
TEXT_SUFFIXES = {".md", ".txt", ".tex", ".yml", ".yaml", ".json", ".csv", ".tsv", ".py", ".ts", ".tsx", ".html"}
# profiles/ holds other people's workspaces; validate_profiles() checks each one on its own terms.
SKIPPED_PARTS = {".venv", "node_modules", "dist", "__pycache__", ".pytest_cache", "output", "migrations", "profiles"}


def fail(message: str) -> None:
    ERRORS.append(message)


def warn(message: str) -> None:
    WARNINGS.append(message)


def built_from(source: Path, pdf: Path) -> bool:
    """The base PDF's QA record says it was compiled from exactly this source and is this PDF.

    File times alone mislead after a copy or a fresh checkout (the .tex can land a moment
    after its PDF); the hashes validate_resume.py records do not.
    """
    import hashlib
    import json

    qa = pdf.parent / "qa.json"
    try:
        record = json.loads(qa.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: E731
    return record.get("source_sha256") == digest(source) and record.get("pdf_sha256") == digest(pdf)


def read(relative_path: str, root: Path = ROOT) -> str:
    path = root / relative_path
    if not path.is_file():
        fail(f"Missing required file: {relative_path}")
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        fail(f"Not UTF-8: {relative_path} ({exc})")
        return ""


def load_yaml_mapping(relative_path: str) -> dict[str, Any] | None:
    from validate_resume import load_yaml
    try:
        value = load_yaml(ROOT / relative_path)
    except (RuntimeError, OSError, ValueError) as exc:
        fail(f"Unable to inspect YAML: {relative_path} ({exc})")
        return None
    if not isinstance(value, dict):
        fail(f"YAML must be a mapping: {relative_path}")
        return None
    return value


def strip_latex_comments(source: str) -> str:
    lines = []
    for line in source.splitlines():
        match = re.search(r"(?<!\\)%", line)
        lines.append(line[: match.start()] if match else line)
    return "\n".join(lines)


def latex_braces_balanced(source: str) -> bool:
    depth = 0
    escaped = False
    for character in strip_latex_comments(source):
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def validate_skill(relative_dir: str, root: Path = ROOT) -> None:
    skill_dir = root / relative_dir
    source = read(f"{relative_dir}/SKILL.md", root)
    match = re.match(r"^---\n(.*?)\n---\n", source, re.DOTALL)
    if not match:
        fail(f"Invalid or missing skill frontmatter: {relative_dir}/SKILL.md")
        return
    frontmatter = match.group(1)
    name_match = re.search(r"^name:\s*([a-z0-9-]+)\s*$", frontmatter, re.MULTILINE)
    if not name_match:
        fail(f"Skill name must use lowercase hyphen-case: {relative_dir}/SKILL.md")
    elif name_match.group(1) != skill_dir.name:
        fail(f"Skill name/folder mismatch: {name_match.group(1)} != {skill_dir.name}")
    if not re.search(r"^description:\s*\S", frontmatter, re.MULTILINE):
        fail(f"Skill description missing: {relative_dir}/SKILL.md")
    if not (skill_dir / "agents/openai.yaml").is_file():
        fail(f"Skill UI metadata missing: {relative_dir}/agents/openai.yaml")


def active_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(ROOT)
        if set(relative.parts) & SKIPPED_PARTS:
            continue
        yield path, relative


def validate_python() -> None:
    for path, relative in active_files():
        if path.suffix != ".py":
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError) as exc:
            fail(f"Python parse failed: {relative} ({exc})")


def validate_no_previous_edition() -> None:
    pattern = re.compile("|".join(re.escape(value) for value in PREVIOUS_EDITION), re.IGNORECASE)
    for path, relative in active_files():
        # The USCIS employer list is public data and legitimately names any employer.
        if relative == Path("backend/scripts/validate_workspace.py") or relative.parts[:2] == ("data", "sponsors"):
            continue
        if relative.as_posix().startswith(PREVIOUS_EDITION_ALLOWED):
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            fail(f"Non-UTF-8 active file: {relative}")
            continue
        found = pattern.search(source)
        if found:
            fail(f"The previous edition's candidate data appears in active content: {relative} ({found.group(0)})")


def validate_profile(profile: dict[str, Any], registry: dict[str, Any]) -> None:
    candidate = profile.get("candidate") or {}
    claims = {c.get("id"): c for c in registry.get("claims", []) if isinstance(c, dict)}
    identity = claims.get("IDENTITY-001", {}).get("value")
    if not candidate.get("full_name") or candidate.get("full_name") != identity:
        fail("profile.yml candidate.full_name must equal the registry's IDENTITY-001 value")
    for field, claim_id in (("email", "CONTACT-EMAIL-001"), ("phone", "CONTACT-PHONE-001")):
        if claims.get(claim_id, {}).get("value") != candidate.get(field):
            fail(f"profile.yml candidate.{field} must equal the registry's {claim_id} value")
    if candidate.get("timezone") != "America/Chicago":
        fail("profile.yml candidate.timezone must be America/Chicago (the app's single timezone)")

    for key in ("identity_guardrails", "target_roles", "role_tracks", "narrative", "claim_policy",
                "location_preferences", "sponsorship", "reapply", "project_selection", "resume_contract", "batch_contract"):
        if key not in profile:
            fail(f"profile.yml is missing the {key} section")

    tracks = profile.get("role_tracks") or []
    codes = [t.get("code") for t in tracks if isinstance(t, dict)]
    if codes != ["A", "B", "C", "D"]:
        fail(f"profile.yml role_tracks must be the four tracks A, B, C, D in order; found {codes}")
    projects = {p.get("id"): p for p in registry.get("projects", []) if isinstance(p, dict)}
    for track in tracks:
        for project_id in track.get("signature_pool") or []:
            if project_id not in projects:
                fail(f"Track {track.get('code')} signature_pool names an unregistered project: {project_id}")
            elif projects[project_id].get("signature_eligible") is False:
                fail(f"Track {track.get('code')} signature_pool names a supporting-only project: {project_id}")
    if (profile.get("target_roles") or {}).get("max_years_required") is None:
        fail("profile.yml target_roles.max_years_required must be set (roles asking for more are screened out)")

    reapply = profile.get("reapply") or {}
    expected = {"ghost_after_days": 21, "reject_cooldown_days": 180, "ghost_cooldown_days": 90}
    for key, value in expected.items():
        if reapply.get(key) != value:
            warn(f"profile.yml reapply.{key} is {reapply.get(key)!r}; Annie's AGENTS.md rule is {value}")

    location = profile.get("location_preferences") or {}
    if "United States" not in str(location):
        fail("profile.yml location_preferences must restrict the search to the United States")

    if CONTRACT.paper != "letter" or CONTRACT.pages != 1:
        fail("resume_contract must be one US Letter page (paper: letter, required_pages: 1)")
    if CONTRACT.min_body_pt < 10:
        fail("resume_contract minimum_body_font_pt may not go below 10; cut content instead")
    if len(CONTRACT.cut_order) < 4:
        fail("resume_contract.cut_order must document the four cuts, in order")


def validate_agents(profile: dict[str, Any]) -> None:
    name = (profile.get("candidate") or {}).get("full_name", "")
    builder = read(f"{SKILLS_DIR}/resume-tailor/SKILL.md", REPO_ROOT)
    for value in (name, "data/context/evidence.yml", "one page", "signature project", "backend/scripts/validate_resume.py"):
        if value and value.lower() not in builder.lower():
            fail(f"The resume-tailor skill is missing its contract: {value}")
    hunter = read(f"{SKILLS_DIR}/job-hunter/SKILL.md", REPO_ROOT)
    for value in (name, "sponsorship", "United States", "sentence"):
        if value and value.lower() not in hunter.lower():
            fail(f"The job-hunter skill is missing its contract: {value}")
    # One rulebook for every AI app: no tool-specific instruction files beside it.
    for stray in ("CLAUDE.md", "career-dashboard/CLAUDE.md", ".claude/skills", ".claude/commands",
                  "career-dashboard/.github/agents"):
        if (REPO_ROOT / stray).exists():
            warn(f"{stray} is back: keep AI instructions in AGENTS.md and skills in {SKILLS_DIR}/")
    policy = read("AGENTS.md")
    for value in (name, "sponsor", "one page", "never", "study plan"):
        if value.lower() not in policy.lower():
            fail(f"AGENTS.md is missing policy text: {value}")


def validate_evidence_registry(registry: dict[str, Any], profile: dict[str, Any]) -> None:
    claims = registry.get("claims")
    projects = registry.get("projects")
    not_resume_ready = registry.get("not_resume_ready", [])
    if not isinstance(claims, list):
        fail("Evidence registry claims must be a list")
        claims = []
    if not isinstance(projects, list):
        fail("Evidence registry projects must be a list")
        projects = []
    if not isinstance(not_resume_ready, list):
        fail("Evidence registry not_resume_ready must be a list")
        not_resume_ready = []

    entries = []
    for section_name, section in (("claims", claims), ("projects", projects), ("not_resume_ready", not_resume_ready)):
        for index, item in enumerate(section, start=1):
            if not isinstance(item, dict):
                fail(f"Evidence registry {section_name}[{index}] must be a mapping")
                continue
            entries.append(item)

    ids = [str(item.get("id", "")) for item in entries]
    malformed = sorted(value or "<missing>" for value in ids if not re.fullmatch(r"[A-Z0-9-]+", value))
    if malformed:
        fail(f"Malformed evidence IDs: {', '.join(malformed)}")
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    if duplicates:
        fail(f"Duplicate evidence IDs: {', '.join(duplicates)}")

    allowed_status = {"confirmed", "user_reported", "conditional", "hold", "missing"}
    for section_name, section in (("claim", claims), ("project", projects)):
        for item in section:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id", "<missing>"))
            refs = item.get("source_refs")
            if not isinstance(refs, list) or not refs or any(not isinstance(r, str) or not r.strip() for r in refs):
                fail(f"Evidence {section_name} {item_id} needs non-empty source_refs")
            if item.get("status") not in allowed_status:
                fail(f"Evidence {section_name} {item_id} has an unknown status: {item.get('status')!r}")
            if not item.get("approved_external_use"):
                fail(f"Evidence {section_name} {item_id} needs approved_external_use")

    for project in projects:
        if not isinstance(project, dict):
            continue
        project_id = str(project.get("id", "<missing>"))
        content = project.get("resume_content")
        if not isinstance(content, dict) or set(content) != {"title", "context", "bullets"}:
            fail(f"Evidence project {project_id} resume_content must contain exactly title, context, bullets")
            continue
        for field in ("title", "context"):
            if not isinstance(content.get(field), str) or not content[field].strip():
                fail(f"Evidence project {project_id} resume_content.{field} must be non-empty text")
        bullets = content.get("bullets")
        if not isinstance(bullets, list) or not 2 <= len(bullets) <= 3 or any(not isinstance(b, str) or not b.strip() for b in bullets):
            fail(f"Evidence project {project_id} resume_content.bullets must contain 2-3 non-empty strings")

    revision = registry.get("candidate_revision")
    if not isinstance(revision, str) or not revision.strip():
        fail("Evidence registry needs a non-empty candidate_revision")
    elif revision != str(profile.get("candidate_revision")):
        fail("Evidence registry candidate_revision must match data/config/profile.yml")

    known = {str(item.get("id")): item for item in entries}
    immutable = (registry.get("immutable_across_resumes") or {}).get("claim_ids") or []
    if not immutable:
        fail("Evidence registry needs immutable_across_resumes.claim_ids")
    for claim_id in immutable:
        if claim_id not in known:
            fail(f"immutable_across_resumes names an unknown claim: {claim_id}")
        elif known[claim_id].get("status") in {"hold", "missing"}:
            fail(f"immutable_across_resumes names a held or missing claim: {claim_id}")


def validate_artifact_contract() -> None:
    expected = list(CONTRACT.required_artifacts)
    if "study-plan.md" not in expected:
        fail("batch_contract.required_artifacts must include study-plan.md (the wall between resume and study plan)")
    previews = [a for a in expected if a.startswith("resume-preview/")]
    if previews != [f"resume-preview/{name}" for name in CONTRACT.preview_files]:
        fail(f"batch_contract.required_artifacts must list exactly {CONTRACT.pages} preview page(s)")
    template = load_yaml_mapping("data/templates/batch.example.yml")
    if template is not None and template.get("required_artifacts") != expected:
        fail("data/templates/batch.example.yml required_artifacts must match profile.yml batch_contract")
    example = load_yaml_mapping("data/templates/evidence-map.example.yml")
    if example is not None:
        registry = load_yaml_mapping("data/context/evidence.yml") or {}
        known = {str(i.get("id")) for group in ("claims", "projects") for i in registry.get(group, []) if isinstance(i, dict)}
        unknown = [i for i in example.get("resume_claim_ids", []) if i not in known]
        if unknown:
            fail("evidence-map.example.yml names unregistered IDs: " + ", ".join(unknown))


def validate_resume() -> None:
    resume = read("data/templates/resume-base.tex")
    if not resume:
        return
    clean = strip_latex_comments(resume)
    if len(re.findall(r"\\usepackage(?:\[[^\]]*\])?\{hyperref\}", clean)) != 1:
        fail("Base resume must load hyperref exactly once")
    if len(re.findall(CONTRACT.documentclass_pattern(), clean)) != 1:
        fail(f"Base resume must use the fixed {CONTRACT.paper.title()} 10pt document class")
    if not clean.rstrip().endswith(r"\end{document}"):
        fail("Base resume does not end with \\end{document}")
    if not latex_braces_balanced(resume):
        fail("Base resume has unbalanced LaTeX braces")
    if CONTRACT.pages == 1 and (r"\newpage" in clean or r"\clearpage" in clean):
        fail("A one-page resume may not contain an explicit page break")
    for value in CONTRACT.required_source_values:
        if value not in clean:
            fail(f"Base resume missing stable registry content: {value}")
    for section in CONTRACT.required_sections:
        if len(re.findall(rf"\\section\{{{re.escape(section)}\}}", clean)) != 1:
            fail(f"Base resume must contain exactly one {section} section")
    for macro in ("SelectedProjectID", "SecondProjectID"):
        if len(re.findall(rf"\\newcommand\{{\\{macro}\}}\{{[^{{}}]+\}}", clean)) != 1:
            fail(f"Base resume must declare exactly one {macro}")
    for label, pattern in CONTRACT.unsafe_patterns.items():
        if re.search(pattern, clean):
            fail(f"Base resume contains unsafe content: {label}")

    source = ROOT / "data/templates/resume-base.tex"
    name = CONTRACT.pdf_author.split()
    pdf = ROOT / "data/output/base" / (f"{name[0]}_{name[-1]}_Resume.pdf" if name else "resume.pdf")
    if not pdf.is_file():
        warn(f"Base resume PDF not built yet: {pdf.relative_to(ROOT)}")
    elif pdf.stat().st_mtime < source.stat().st_mtime and not built_from(source, pdf):
        fail("Base resume PDF is stale; recompile it from data/templates/resume-base.tex")


def validate_sponsorship() -> None:
    rules = load_yaml_mapping("data/config/sponsorship.yml")
    if rules is None:
        return
    for key in ("negation_guards", "cap_exempt_signals"):
        if not rules.get(key):
            fail(f"data/config/sponsorship.yml is missing {key}")
    csv_path = ROOT / "data/sponsors/sponsors-uscis.csv"
    if csv_path.is_file():
        with csv_path.open(encoding="utf-8", newline="") as handle:
            rows = sum(1 for _ in csv.reader(handle)) - 1
        if rows < 10000:
            fail(f"USCIS sponsor history looks truncated ({rows} rows)")
    from backend.services.sponsorship import screen
    refusal = "Must be authorized to work in the United States without sponsorship now or in the future."
    if screen(refusal).verdict != "EXCLUDED":
        fail("Sponsorship gate no longer excludes a plain refusal sentence")
    for kept in ("Build streaming pipelines with Kafka.", "No security clearance required for this position."):
        if screen(kept).verdict != "KEEP":
            fail(f"Sponsorship gate wrongly excludes: {kept}")


def validate_layout() -> None:
    """The mirrored layout: career-dashboard/, daily-job-search/, backup/ at the repo root."""
    for required in ("daily-job-search/with_resume_runtime.py", "daily-job-search/history.csv"):
        if not (REPO_ROOT / required).is_file():
            fail(f"Missing sibling runtime file: {required}")
    history = REPO_ROOT / "daily-job-search/history.csv"
    if history.is_file():
        header = history.read_text(encoding="utf-8").splitlines()[:1]
        if header != ["date,company,role,url,requisition_id,location,status,artifact_dir"]:
            fail("daily-job-search/history.csv header changed; agents.py reads these columns")
    for retired in ("system", "dashboard", "output", "context"):
        if (REPO_ROOT / retired).exists():
            fail(f"Pre-port folder still at the repo root (it belongs in backup/): {retired}")
    if not (REPO_ROOT / "backup").is_dir():
        warn("backup/ is missing; the pre-port snapshot is gone")


def validate_profiles() -> None:
    """Every built profile besides Annie: its files exist, parse, and describe one consistent workspace."""
    import yaml

    sys.path.insert(0, str(ROOT))
    from backend.profiles import ProfileStore
    from backend.resume_contract import contract_for

    store = ProfileStore(base=ROOT / "profiles", legacy_root=ROOT)
    for profile in store.list():
        if profile.get("legacy") or profile["state"] != "ready":
            continue
        root = store.root_for(profile["id"])
        label = f"Profile {profile['id']}"
        for relative in ("data/config/profile.yml", "data/config/sponsorship.yml", "data/config/portals.yml",
                         "data/context/evidence.yml", "data/templates/resume-base.tex", "AGENTS.md"):
            if not (root / relative).is_file():
                fail(f"{label} is missing {relative}")
        try:
            own = yaml.safe_load((root / "data/config/profile.yml").read_text(encoding="utf-8")) or {}
            registry = yaml.safe_load((root / "data/context/evidence.yml").read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            fail(f"{label}: profile.yml or evidence.yml cannot be read ({exc})")
            continue
        ids = [item.get("id") for group in ("claims", "projects") for item in registry.get(group) or []]
        if len(ids) != len(set(ids)):
            fail(f"{label}: duplicate evidence IDs")
        identity = next((c.get("value") for c in registry.get("claims") or [] if c.get("id") == "IDENTITY-001"), None)
        if identity != (own.get("candidate") or {}).get("full_name"):
            fail(f"{label}: profile.yml candidate.full_name must equal the registry's IDENTITY-001 value")
        if not (ROOT / "backend/countries" / str(own.get("country_pack") or "") / "pack.yml").is_file():
            fail(f"{label}: country_pack {own.get('country_pack')!r} has no pack in backend/countries/")
        try:
            contract = contract_for(root)
            if contract.pages != 1:
                warn(f"{label}: resume_contract asks for {contract.pages} pages")
        except Exception as exc:  # noqa: BLE001 - reported, the rest still runs
            fail(f"{label}: its resume contract does not load ({exc})")


def main() -> int:
    for required in REQUIRED_FILES:
        read(required)
    for yaml_file in ("data/config/portals.yml", "data/config/regions.yml", "data/templates/batch.example.yml"):
        load_yaml_mapping(yaml_file)
    read("AGENTS.md", REPO_ROOT)
    for skill in REQUIRED_SKILLS:
        validate_skill(f"{SKILLS_DIR}/{skill}", REPO_ROOT)
        load_yaml_mapping(f"../{SKILLS_DIR}/{skill}/agents/openai.yaml")
    validate_python()
    validate_no_previous_edition()
    profile = load_yaml_mapping("data/config/profile.yml") or {}
    registry = load_yaml_mapping("data/context/evidence.yml") or {}
    validate_profile(profile, registry)
    validate_agents(profile)
    validate_evidence_registry(registry, profile)
    validate_artifact_contract()
    validate_resume()
    validate_sponsorship()
    validate_layout()
    validate_profiles()

    for message in WARNINGS:
        print(f"WARN: {message}")
    if ERRORS:
        for message in ERRORS:
            print(f"FAIL: {message}")
        print(f"\nWorkspace validation failed with {len(ERRORS)} error(s).")
        return 1
    print("PASS: Annie's profile, registry, sponsorship gate, agents, workflows, layout and base resume are consistent"
          " (and every other built profile's files).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
