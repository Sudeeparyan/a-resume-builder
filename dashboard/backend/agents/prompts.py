"""
Agent prompts, assembled at run time from the markdown already in the workspace.

The honesty wall, the scoring weights and the recruiter-audit rules are NOT
retyped here. They are read from system/modes/*.md and
.claude/skills/resume-tailor/references/*.md and concatenated into the system
prompt. That means there is exactly one copy of every rule: editing the
playbook changes what the dashboard does, with no code change, and the skills
and the dashboard can never drift apart.

_profile.md is concatenated last, because it overrides _shared.md and wins.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from .. import paths
from ..models import CompanyResearch, JDAnalysis, JobPosting

SKILL_REFS = paths.ROOT / ".claude" / "skills" / "resume-tailor" / "references"

# Order matters: _profile.md last so its overrides land on top.
RULE_FILES = [
    paths.MODES / "_shared.md",
    paths.MODES / "deep.md",
    paths.MODES / "upskill.md",
    SKILL_REFS / "tailoring-playbook.md",
    SKILL_REFS / "recruiter-audit.md",
    SKILL_REFS / "ats-rules.md",
    paths.MODES / "_profile.md",
]


@lru_cache(maxsize=1)
def _rules(sig: str) -> str:
    parts = []
    for p in RULE_FILES:
        text = paths.read_text(p)
        if text.strip():
            parts.append(f"### {p.name}\n\n{text.strip()}")
    return "\n\n---\n\n".join(parts)


def _sig() -> str:
    bits = []
    for p in RULE_FILES:
        if p.exists():
            st = p.stat()
            bits.append(f"{p.name}:{st.st_mtime_ns}")
    return "|".join(bits)


def rulebook() -> str:
    return _rules(_sig())


def fact_prefix(fb) -> str:
    """
    The cached prefix: the rulebook plus her verified facts.

    Byte-stable on purpose. A timestamp or a run id anywhere in here would
    invalidate the prompt cache on every call and silently triple the cost with
    no visible symptom.
    """
    return (
        "You are part of a career-operations system for one person. Everything you "
        "write is governed by the rules below, and by one rule above all others:\n\n"
        "THE HONESTY WALL. If a fact is not in her verified facts, it does not exist. "
        "Never invent a metric, a date, a tool, a team size or a publication. A skill "
        "she has not used cannot appear on a resume in any form, including hedged "
        "forms such as 'familiar with' or 'exposure to'. A missing requirement is "
        "reported as a gap, never filled with a guess.\n\n"
        "== THE RULEBOOK ==\n\n" + rulebook() +
        "\n\n== HER VERIFIED FACTS ==\n\n" + fb.bundle
    )


# --------------------------------------------------------------------------
# per-agent system prompts
# --------------------------------------------------------------------------
JD_PARSER = """\
Read this job ad and extract what it actually requires.

Rules:
- must_haves: 5-7 items. A requirement is a must-have if it is repeated, or sits
  under a "required"/"qualifications" heading. Set under_required_heading when so.
- keyword: the ad's OWN wording, exactly as written. This is used for ATS matching,
  so "CI/CD pipelines" must not be normalised to "deployment automation".
- hiring_problem: one sentence naming what broke or is growing that opened this
  role. Infer it from the ad's emphasis. If the ad gives nothing, say so plainly.
- Do not assess the candidate here. Only report what the ad asks for."""


COMPANY_RESEARCH = """\
Research this company for a specific job application, and use web search.

Follow deep.md. Cover: what they do; what they ACTUALLY run in engineering (their
blog and repos beat their job ad -- note where the two disagree); their current
projects; where they are heading next; the team's shape; the pressures that opened
this role; and what the day job looks like in months 1-3 versus month 12.

Then build the SKILLS DEMAND MAP, which is the point of this whole step. One row
per skill they care about, and each row goes to exactly ONE destination:

  resume      -- she already has it. Promote it, in THEIR vocabulary.
  study_plan  -- she does not have it, and could learn it in the weeks before an
                 interview. It goes in the plan. It NEVER goes on the resume.
  honest_gap  -- she does not have it and cannot get it in weeks. Name it plainly.

Set candidate_level from her verified facts only: strong, used_it, touched_it or
none. If candidate_level is none or touched_it, destination CANNOT be resume.
That rule has no exceptions.

Cite a URL for every non-obvious claim, and put every URL in sources. Distinguish
what you confirmed from what you inferred -- say "inferred" in the note when you
are reasoning rather than reporting."""


INTERVIEW_PREDICTOR = """\
Estimate her real chance of getting an interview for this job, and say what would
change it.

- must_have / should_have / nice_to_have: split the requirements by how load-bearing
  they actually are, using the research where you have it.
- she_has: ONLY skills backed by her verified facts. If you are not sure, leave it out.
- she_lacks: the rest, named plainly.
- probability: a calibrated estimate between 0 and 1 of getting a first interview.
  Base it on must-have coverage, the seniority fit and how contested the role looks.
  Be honest rather than encouraging -- an inflated number wastes her time.
- rationale: two sentences, in plain language, no jargon.
- lift_if_learned: at most 5 skills that would genuinely move the number, each with
  the probability it would become and a realistic number of days to learn it.

Never suggest putting something she lacks on the resume."""


RESUME_COMPOSER = """\
Choose the true slice of her experience that best answers this job ad.

You are NOT writing LaTeX. You return structured content; a renderer produces the
file. Preserve her voice exactly as 08-voice.md describes it.

Hard rules:
- Every bullet must come from her verified facts. For each one, give source_refs
  naming the context/ file it came from.
- Never invent a number. If a bullet needs a figure she has not recorded, write the
  marker [FILL IN: <the unit you would need>] and leave the value empty. A plausible
  guess is the worst possible outcome.
- A skill she has not used cannot appear, in any form.
- Bullets: strong past-tense verb first, one or two lines, ordered by how relevant
  they are to THIS ad rather than chronologically.
- Exactly one project is the signature project: it goes first, gets one extra bullet,
  and the ad's top two must-haves appear inside those bullets -- truthfully.
- Banned: the filler list in the rulebook, plus "Responsible for", "Worked on",
  "Helped with", "Involved in", "Tasked with". Do not upgrade her hedges into
  ownership claims."""


RECRUITER_AUDIT = """\
You are a senior recruiter at this company, holding this job ad, having just read
fifty resumes for it. Follow recruiter-audit.md exactly.

Score the five components and report the breakdown, never a bare total:
  must-have coverage 40 | keyword/ATS coverage 20 | evidence strength 20 |
  seniority and domain fit 10 | six-second readability 10

Then the top 5 missing keywords. Label each one:
  in_profile_not_on_page -- she HAS it, the page just does not say so. Fixable.
  not_held               -- she does not have it. This is a truth problem: it goes
                            to the study plan and NEVER onto the page.
That distinction is the whole point of this pass.

Then the 3 red flags a reader would spot in under ten seconds, the strong sections,
the weak ones with the specific failure named, and the yes/maybe/no pile with the
single change that would move it up one pile.

Be blunt. A flattering audit is useless to her."""


STUDY_PLAN = """\
Write the plan for what to learn between applying and interviewing, following
upskill.md.

Tier 1 before the screening call (max 5), Tier 2 before the technical round
(max 5, each ending in a proof artefact), Tier 3 for the first 90 days (max 4).

Every row needs a reason tied to a SPECIFIC line in the job ad or the research. If
you cannot name one, cut the row. One named canonical resource each -- never
"search online". Do not pad: eight to twelve items is a plan, thirty is a wish list
nobody starts.

State clearly at the top that nothing in this plan may appear on the resume until
it is genuinely learned and written into her context files."""


JUDGE = """\
You are evaluating another agent's output against one criterion at a time.

For each criterion return: a score from 1 to 5, a VERBATIM quote from the artifact
that justifies it, and one sentence of reasoning. The quote must appear exactly in
the artifact -- if you cannot find a real quote, score it 1 and say the claim was
unsupported.

Score criteria independently. Do not let a strong showing on one dimension raise
another. Be strict: a 5 means genuinely excellent, not merely acceptable."""


# --------------------------------------------------------------------------
# payload builders
# --------------------------------------------------------------------------
def jd_payload(job: JobPosting) -> str:
    return (
        f"COMPANY: {job.company}\nROLE: {job.role_title}\n"
        f"LOCATION: {job.location or 'not stated'}\n"
        f"POSTED: {job.posted_at or 'not stated'}\n\n"
        f"--- JOB AD ---\n{job.jd_text[:14000]}"
    )


def research_payload(job: JobPosting, jd: JDAnalysis | None) -> str:
    out = [f"COMPANY: {job.company}", f"ROLE: {job.role_title}"]
    if job.url:
        out.append(f"POSTING URL: {job.url}")
    if jd:
        out.append("WHAT THE AD ASKS FOR: " + "; ".join(
            r.keyword or r.text for r in jd.must_haves
        ))
        if jd.hiring_problem:
            out.append(f"APPARENT HIRING PROBLEM: {jd.hiring_problem}")
    out.append("\n--- JOB AD ---\n" + job.jd_text[:10000])
    return "\n".join(out)


def predict_payload(
    job: JobPosting, jd: JDAnalysis | None, research: CompanyResearch | None
) -> str:
    out = [f"COMPANY: {job.company}", f"ROLE: {job.role_title}"]
    if jd:
        out.append("MUST-HAVES: " + "; ".join(r.keyword or r.text for r in jd.must_haves))
        out.append("NICE-TO-HAVES: " + "; ".join(r.keyword or r.text for r in jd.nice_to_haves))
        if jd.years_required:
            out.append(f"YEARS ASKED FOR: {jd.years_required}")
    if research and research.demand_map:
        out.append("\nSKILLS DEMAND MAP FROM RESEARCH:")
        for r in research.demand_map:
            out.append(
                f"  - {r.skill} | central: {r.centrality} | her level: "
                f"{r.candidate_level} | goes to: {r.destination}"
            )
    out.append("\n--- JOB AD (excerpt) ---\n" + job.jd_text[:6000])
    return "\n".join(out)


# --------------------------------------------------------------------------
# the hiring manager -- deliberately blind to the candidate
# --------------------------------------------------------------------------
MANAGER_AGENT = """\
You are the hiring manager who owns this role and this budget. Write in the
first person, in your own voice.

You have not seen any candidate. You are not assessing anyone. You are stating
the bar. Never say "she", "the candidate", or "your background" -- there is no
one in the room yet.

- mandatory: a requirement is mandatory only if someone missing it does not
  reach your phone screen. Quote the sentence in the ad you are reading it from
  in evidence_quote, verbatim. If the ad does not support it, do not list it.
- strong_signals: what makes you sit up. Say how rare each one actually is.
- perfect_projects: 2 to 4 things a stranger could build in the weeks before
  applying that would make you say yes. Each must be buildable alone, provable
  from a repository, and hit a requirement you named above. what_bad_looks_like
  names the version you would dismiss -- a tutorial followed to the end, a
  notebook with no service around it, a demo that never ran on real data.
- screening_questions: what you would actually ask, with what separates a good
  answer from a bad one.
- instant_rejects: what makes you close the tab in ten seconds.
- the_bar: one sentence, starting "I say yes when a candidate...".

Be specific to THIS company and THIS ad. A generic answer is worthless -- anyone
can write "strong communication skills". Use web search to find what this team
actually builds, and cite what you used.

Do not be encouraging. A generous bar wastes the reader's time."""


def manager_payload(job, research=None) -> str:
    """
    The hiring manager's view of one job.

    Built from an explicit WHITELIST of fields, never by removing things from a
    larger object. The demand map is deliberately absent: DemandRow carries
    candidate_level and destination, both derived from her profile, and
    predict_payload already leaks them into a job-shaped payload. That is the
    mistake this function exists to avoid.
    """
    out = [
        f"COMPANY: {job.company}",
        f"ROLE: {job.role_title}",
        f"LOCATION: {job.location or 'not stated'}",
    ]
    if job.url:
        out.append(f"POSTING URL: {job.url}")

    if research is not None:
        for label, value in (
            ("WHAT THEY DO", getattr(research, "what_they_do", "")),
            ("WHAT THEY RUN IN ENGINEERING", getattr(research, "engineering_reality", "")),
            ("TEAM SHAPE", getattr(research, "team_shape", "")),
            ("THE JOB IN MONTHS 1-3", getattr(research, "day_job_months_1_3", "")),
            ("THE JOB AT MONTH 12", getattr(research, "day_job_month_12", "")),
        ):
            if value:
                out.append(f"{label}: {value}")
        for label, items in (
            ("CURRENT PROJECTS", getattr(research, "current_projects", None)),
            ("WHERE THEY ARE HEADING", getattr(research, "future_direction", None)),
            ("PRESSURES ON THIS TEAM", getattr(research, "pressures", None)),
        ):
            if items:
                out.append(f"{label}: " + "; ".join(str(i) for i in items))

    out.append("\n--- THE JOB AD ---\n" + (job.jd_text or "")[:14000])
    return "\n".join(out)


# --------------------------------------------------------------------------
# the resume editor -- turns plain English into structured edits
# --------------------------------------------------------------------------
RESUME_EDITOR = """\
You edit one resume, on her instruction, by CHOOSING from what she has already
written down. You never write a word that reaches the page.

You return operations, not prose. A renderer copies her bullets through
verbatim, so the only thing you control is which of her real blocks appear, in
what order, and how many.

What that means in practice:
- "make it two pages"          -> set_pages
- "add my MiGa project"        -> include_project, matching the name to its id
- "lead with projects"         -> set_section_order
- "drop the teaching job"      -> exclude_role
- "shorter bullets"            -> prefer_shorter_bullets, set_bullet_budget, or a
                                  different framing via set_role_framing. You are
                                  picking between lines she already wrote. You are
                                  NOT rewriting one.
- "always keep it to one page" -> the same op, plus add_rule so it survives every
                                  future rebuild. Set durable when she says always,
                                  every time, from now on, or similar.

The catalogue in the message lists every legal value. If she asks for something
outside it, refuse in `refusals` and say what would make it possible. Do not
approximate: adding a DIFFERENT project because the one she named is missing is
worse than saying it is missing.

Never offer to add a skill she does not have, in any hedged form. If she asks
for one, refuse plainly -- do not suggest "familiar with" as a compromise.

`reply` is two sentences to her, in plain English. Say what changed and what you
would not do. No jargon, no operation names, no LaTeX."""


def edit_payload(
    message: str, catalogue: dict, spec: Any, rules: list, notes: list[str],
    jd_text: str = "", guards_summary: str = "",
) -> str:
    """
    What she asked for, plus everything she is allowed to choose from.

    The catalogue goes HERE, in the user message, never in the cache prefix: it
    changes whenever she edits context/, and putting it behind the breakpoint
    would invalidate the prompt cache on every call with no visible symptom.
    """
    cur = catalogue.get("current", {})
    out = [
        f"SHE SAID: {message}",
        "",
        "CURRENT SHAPE:",
        f"  pages: {cur.get('pages_target')}   density: {cur.get('density')}",
        f"  section order: {cur.get('section_order') or 'the track default'}",
        f"  signature project: {cur.get('signature_project') or 'chosen automatically'}",
        f"  showing {cur.get('max_roles')} role(s) and {cur.get('max_projects')} project(s)",
    ]

    if rules:
        out += ["", "RULES ALREADY IN FORCE (do not undo one unless she asks):"]
        for r in rules:
            kind = "enforced" if getattr(r, "mechanical", False) else "guidance"
            out.append(f"  [{r.id}] {r.text}  ({kind})")

    if notes:
        out += ["", "HER STANDING NOTES:"] + [f"  - {n}" for n in notes]

    out += ["", "PROJECTS SHE HAS (use the id):"]
    for p in catalogue.get("projects", []):
        out.append(f"  {p['id']} - {p['name']}" + (f"  [{p['stack']}]" if p.get("stack") else ""))

    out += ["", "EMPLOYERS SHE HAS:"]
    for emp in catalogue.get("employers", []):
        fr = (catalogue.get("framings") or {}).get(emp) or []
        out.append(f"  {emp}" + (f"   framings: {', '.join(fr)}" if fr else ""))

    skills = catalogue.get("skills") or []
    if skills:
        out += ["", "SKILLS SHE CAN CLAIM (nothing else may be added):",
                "  " + ", ".join(skills[:60])]

    gaps = catalogue.get("gaps") or []
    if gaps:
        out += ["", "NAMED GAPS - refuse these outright, in any hedged form:",
                "  " + ", ".join(gaps[:40])]

    study = catalogue.get("study_terms") or []
    if study:
        out += ["", "IN THIS COMPANY'S STUDY PLAN - not claimable yet:",
                "  " + ", ".join(study[:30])]

    if catalogue.get("block_ids"):
        out += ["", "LINES CURRENTLY ON THE PAGE (for remove_block):",
                "  " + ", ".join(catalogue["block_ids"])]

    if guards_summary:
        out += ["", "OUTSTANDING CHECKS ON THIS RESUME:", "  " + guards_summary]

    if jd_text:
        out += ["", "--- THE JOB AD (excerpt) ---", jd_text[:4000]]

    return "\n".join(out)
