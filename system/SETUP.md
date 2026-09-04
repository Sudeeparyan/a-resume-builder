# Setup — from nothing to a tailored resume

Time: ~30 minutes the first time, ~2 minutes per job after that.

> **You are not expected to run any of this yourself.** This workspace is driven by an AI assistant
> (Claude Code, GitHub Copilot, or Codex). You talk to it in plain English; **it** runs every command
> and edits every file. Commands are printed so the assistant knows what to do — they are its
> instructions, not your homework. New here? Start with **[START_HERE.md](../START_HERE.md)**.

---

## Step 0 — Get your own copy of the folder

Make a copy of this whole folder so it's yours (Windows: right-click → Copy → Paste; Mac: duplicate).
Rename it to something like `career-jane`. **One folder per person**, and you work in the copy.

<sub>Optional, for the curious: the assistant can version it with `git init` so you can undo
changes — you don't need this to use the workspace.</sub>

---

## Step 1 — Fill in `context/`

This is the only step that needs you, and it's the one that decides how good everything else is.

Open [`context/`](../context/) and work through the numbered files. Write what you know, skip what
you don't — bullet points and half-sentences are fine.

**Or don't type at all:** say *"help me fill in my context"* and the assistant interviews you in plain
questions and writes the files itself. That's the intended path for anyone who'd rather talk.

Drop any documents you have — old CVs, transcripts, LinkedIn exports, certificates — into
[`context/files/`](../context/files/) and say *"I've added files"*. A transcript is the fastest way to
get every module listed, and old CVs routinely hold facts people have forgotten.

**What matters most:**

- **Every module** you studied (`02-education.md`) — not a curated few. A job that names a topic can
  only be matched to a module that's written down.
- **Every project** you've built (`04-projects.md`) — five is workable, ten is strong. Each resume
  leads with a *different* one, so a thin project bank means repetitive resumes.
- **What you're looking for** (`07-preferences.md`) — this steers the job search itself: titles,
  cities, salary floor, hard limits, companies to skip.

Nothing here is extractive-optional: the intake never invents. If a fact isn't in `context/`, it can
never appear on a resume.

---

## Step 2 — Let it build the knowledge base

Say:

```
run profile-intake
```

or just *"Set up my profile."*

It reads every file in `context/` plus everything in `context/files/`, then writes:

| File | What it holds |
|------|---------------|
| `system/config/profile.yml` | Your identity block, tracks, target roles, compensation |
| `system/profile/master-profile.md` | Every claimable fact, structured, with tags for matching |
| `system/profile/positioning.md` | Your two tracks, framing, project reframing map, honest gaps |
| `system/profile/skills-matrix.md` | Skills grouped and levelled, plus the keyword bank |
| `system/profile/interview-stories.md` | A STAR story per project or role |

These are a **tidied copy** of `context/`, built for speed. `context/` stays the original and wins on
any disagreement. Change `context/`, say *"I've updated my context"*, and this copy is rebuilt.

It ends with a gaps report and asks you about anything ambiguous — answer in chat and it writes the
answers into `context/` for you.

---

## Step 3 — Check it's healthy

Ask: **"Is my context ready?"**

The assistant runs `python3 system/scripts/doctor.py` and tells you in plain words. It checks:

1. Which `context/` files still need filling
2. Whether the essentials (name, contact, city, tracks) are in place
3. That the config files parse and the resume templates are sound
4. That no generated resume went out with `{{PLACEHOLDERS}}` or `[FILL IN]` markers left in it
5. How many "did you forget to add it?" questions are waiting in `context/QUESTIONS-FOR-YOU.md`

---

## Step 4 — Get resumes

**One job:** paste the job ad (or a link) and say *"tailor my resume for this"*.

**Ten jobs:** *"Give me 10 companies in Ireland this week with working links, and a resume for each."*

Either way, check [`output/SUMMARY.md`](../output/SUMMARY.md) afterwards — one page listing every
resume made, every company found, what was skipped and why, and what to study this week. Each job also
gets its own folder, `output/NN_Company_Role/`, with the resume, the company research, the study plan
and the job ad in it.

---

## Step 5 — Turn a resume into a PDF

Say **"turn resume 3 into a PDF"**. Either:

- The assistant runs `bash system/scripts/build_pdf.sh output/03_Company_Role/resume.tex`, or
- It walks you through [overleaf.com](https://overleaf.com) — free, paste the file, one button, and
  it refuses to build while any `{{PLACEHOLDER}}` or `[FILL IN]` marker remains.

Don't want LaTeX at all? Say **"give me a plain Word-style resume instead"**.

---

## The loop that makes it better over time

1. A job asks for something not in your `context/` → the assistant flags it and logs it in
   `context/QUESTIONS-FOR-YOU.md`.
2. You say *"yes, I did that"* → it writes the fact into the right `context/` file.
3. Every future resume can use it, automatically.

Same for learning: finish something from a study plan, say *"I finished the Docker one"*, and it moves
from the study plan into your profile — the one route by which anything reaches a resume.

---

## Adding a different country

Ireland is pre-filled in `system/config/regions.yml`. To target elsewhere, copy the `ireland:` block,
edit the boards, hubs, work-authorisation routes and CV conventions, and set `default_region` to the
new slug. Or just ask the assistant to do it.
