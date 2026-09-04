# Data contract — what's yours vs what's the system's

This template is meant to be **shared** and **copied per person**. This file draws the line between
files that hold *your* data (never overwrite these when you pull a template update) and files that
are generic system logic (safe to replace with a newer version).

The three-folder layout makes the line almost trivial:

| Folder | Layer |
|--------|-------|
| `context/` | **100% yours.** Never touched by an update. Never written by the assistant, except `QUESTIONS-FOR-YOU.md` |
| `output/` | **100% yours.** Everything the assistant produced for you |
| `system/` | Mostly the system's — with three exceptions listed below |

## User layer — YOUR data (never auto-update)

| Path | What it is |
|------|-----------|
| `context/**` | Everything you've told the system about yourself, plus `context/files/` |
| `context/QUESTIONS-FOR-YOU.md` | The ⚠️ ledger. The assistant writes it; you answer it |
| `output/SUMMARY.md` | Your one-page view: resumes made, companies found, what to study |
| `output/NN_Company_Role/**` | Every application's resume, research, study plan, cover letter, job ad |
| `system/config/profile.yml` | Your identity, tracks, targets, comp — derived from `context/` |
| `system/modes/_profile.md` | Your overrides (scoring, no-go companies, tone) |
| `system/profile/**` | The tidied knowledge base built from `context/` |
| `system/data/**` | Applied-companies list, company notes, signature-project registry, scan history |

**Regenerable vs irreplaceable.** `context/` is irreplaceable — it is the only place your facts
exist. Everything in `system/profile/`, `system/data/` and `output/` can be rebuilt from `context/`
by re-running `profile-intake` and re-tailoring. Back up `context/`; the rest is a cache.

## System layer — generic logic (safe to update)

| Path | What it is |
|------|-----------|
| `CLAUDE.md`, `system/modes/_shared.md` | Read order, scoring, ATS + honesty rules |
| `system/modes/scan.md`, `evaluate.md`, `deep.md`, `batch.md`, `upskill.md` | Mode logic |
| `.claude/skills/**` | Skill definitions (intake, tailor, hunter, interview, verify) |
| `.github/agents/**` | Copilot agents + workflows |
| `system/config/regions.yml`, `portals.yml` | Market packs and search config (generic market facts) |
| `system/templates/**` | LaTeX / Markdown / doc bases |
| `system/scripts/**` | init_profile, doctor, ats_check, build_pdf, verify_job_url |
| `system/examples/**` | Fictional reference examples |
| `START_HERE.md`, `README.md`, `system/SETUP.md`, `system/PLACEHOLDERS.md` | Documentation |

## The rule

- **User-layer file:** no update may read, modify, or delete it.
- **System-layer file:** can be replaced wholesale with a newer version.
- Personal data **never** goes in a system-layer file. That is why customisation lives in
  `context/`, `system/modes/_profile.md` and `system/profile/` — not in `system/modes/_shared.md`
  or the skills.
- The assistant **never writes into `context/`** except `QUESTIONS-FOR-YOU.md`, or when the user
  explicitly asks it to record something ("I built X", "I finished the AWS course") — and then it
  says which file it wrote to.
