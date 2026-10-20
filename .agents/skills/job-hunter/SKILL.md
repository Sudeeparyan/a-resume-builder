---
name: job-hunter
description: >-
  Find, verify, sponsorship-screen, rank and save United States job openings for Annie Prasanna
  Manoharan. Use when asked to "find jobs", "search for roles", "what should I apply to this week",
  "scan companies", "refresh the job list", "give me 10 jobs", or to check a specific company's
  openings. Runs the hard sponsorship gate and the never-re-apply rules through the career-dashboard
  app, so an excluded, already-applied or recently-rejecting company is never surfaced. United States
  only. Never invents a listing or a link.
---

# Job hunter

Everything runs through the app in `career-dashboard/`. `career` means `.\career.cmd` on Windows or
`./career` on macOS, Linux and Git Bash (see the root `AGENTS.md`).

## Read first

`career-dashboard/AGENTS.md`, then `career-dashboard/data/context/` (Annie's own words; they win every
conflict; especially `07-preferences.md` and `01-basics.md`), `data/config/profile.yml`,
`data/context/evidence.yml`, `data/config/sponsorship.yml`, and `backend/workflows/modes/_shared.md`,
`_profile.md` and `scan.md` (the full procedure). If a preference is still open in
`QUESTIONS-FOR-YOU.md`, ask her plainly and offer to record the answer.

## Candidate

Annie Prasanna Manoharan: MS Computer Engineering (University of Arkansas, May 2026), Data Engineering
Intern at InsOps Inc., AICV Lab research assistant and teaching assistant, previously Soliton
Technologies (Engineering Intern, then Project Engineer; Dräger medical-device test automation). Entry
level, four tracks: Data / Analytics Engineering, ML / AI Engineering, Software Engineering,
Embedded / Test Automation. She is on active F-1 OPT: authorized to work in the United States now,
sponsorship needed later.

## The rules you enforce

- **Sponsorship gate** (`career ws sponsor-check --company "<name>" --file <jd.txt>`): an explicit
  refusal, or a US citizenship / permanent residency / security clearance / ITAR/EAR / US-person
  requirement, excludes the posting; it is logged with the exact sentence so a wrong call can be
  restored. Silence is shown; an offer to sponsor is shown and ranked top. "Must be authorized to work
  in the United States" and "no clearance required" never exclude her.
- **Sponsorship history ranks, never excludes**: H-1B history, E-Verify and cap-exempt status give the
  tiers S (cap-exempt) → A (says it sponsors) → B (proven H-1B sponsor) → C (silent).
- **Never re-apply** (`career ws check-reapply --company "<name>" --title "<role>"`): same company and
  role never again; rejected → company hidden 180 days; applied and quiet 21 days → ghosted, open again
  after 90 days for a different role only.
- **Role fit**: four tracks, entry level, ≤4 years, United States or Remote (US). Reject senior titles,
  anything asking for more than 4 years, non-US locations, web/full-stack and DevOps/platform roles,
  even when "data" or "engineer" is in the title.

## Steps

1. Tracked career pages: `career ws run --kind discovery --preset portals` (Greenhouse, Lever and Ashby
   feeds; no AI call).
2. AI discovery: `career ws run --kind discovery` (or `--preset balanced_five`). It runs on the app's
   Auto route: her Kimi, Codex and Claude plans first, Azure only if all three are out
   (`career ws ai-status` shows which plans are resting).
3. By hand: Indeed `search_jobs` (country `US`) and `get_job_details` for the full JD; employer and ATS
   pages beat aggregators. Quote restrictive sentences verbatim.
4. Validate title, company, US location, description and an active application route; verify links
   with the `verify-job-url` skill.
5. Gate, then save: `career add --file <job.json>` (it runs the gate and the re-apply check itself).
   Save excluded postings too, so they show under Excluded roles with their sentence.
6. For a requested count, excluded, duplicate, expired and inaccessible leads do not consume it; keep
   searching until the count is met or the search is honestly exhausted, and report the coverage.
7. Report a ranked table (tier, score, company, role, location, link), the excluded postings with their
   sentences, and one plain next step. `career-dashboard/data/output/SUMMARY.md` refreshes itself.

For "give me N jobs **and** resumes", switch to the `hunt` skill. Never apply or contact anyone.
