# Start here 👋

This turns *your* background into a resume written for one specific job — a different one for every
company, without you rewriting anything.

**You don't need to know any code.** You never open a terminal or run anything. You type in plain
English and the AI does the work.

---

## There are only three folders

| Folder | Whose it is | What's in it |
|--------|-------------|--------------|
| 📥 **[context/](context/)** | **Yours.** The only folder you touch | Everything about you: education, jobs, projects, skills, what you're looking for |
| 📤 **[output/](output/)** | The AI's work for you | **[SUMMARY.md](output/SUMMARY.md)** — one page showing everything it did — plus one folder per job |
| ⚙️ **system/** | The machinery | Ignore it. It's the AI's instruction manual |

That's the whole layout.

---

## Step 1 — Fill in `context/` (once, ~30 minutes)

Open **[context/](context/)** and work through the numbered files. Write what you know, skip what
you don't. Bullet points and half-sentences are fine — nothing needs to be neat.

Prefer to talk instead of type? Say **"help me fill in my context"** and the AI will just ask you
questions and write the files for you.

Got an old CV, a transcript, a LinkedIn export? Drop them into **[context/files/](context/files/)**
and say *"I've added files"*.

> **The one thing worth doing properly:** list **every module** you studied and **every project**
> you've built — including college assignments and things you think are too small to count. That's
> what the AI selects from. A module you forget to mention can't win you an interview.

When you're done, ask: **"Is my context ready?"** — it checks and tells you in plain words.

---

## Step 2 — Ask for what you want

| You want… | Type this |
|-----------|-----------|
| **A resume for one job** | Paste the job ad (or a link), then *"tailor my resume for this"* |
| **Jobs *and* resumes together** | *"Give me 10 companies in Ireland this week with working links, and a resume for each"* → **you get 10 folders in `output/`, 10 different resumes** |
| **A cover letter** | *"Write a cover letter for job 3"* |
| **Interview prep** | *"Prep me for the Stripe interview"* |
| **To know what to study** | *"What should I study this week?"* — it looks across every job you've applied to and names the one skill that helps most |
| **To add something new** | *"I finished the AWS course"* or *"I built the dashboard project"* — it goes into your profile, and every future resume can use it |

---

## Where to look afterwards

**[output/SUMMARY.md](output/SUMMARY.md) is the one page to read.** Every time you ask for jobs or
resumes, it updates itself:

- **Your resumes** — every resume made, which company, the match score, the apply link, where it's at
- **Companies found, no resume yet** — the shortlist from the last search, links already checked
- **Considered and skipped** — what was ruled out and why, so you can see nothing was missed
- **What to study this week** — the one skill that helps across the most of your applications

Next to it sits one folder per job — `output/01_Sanofi_QCAnalyst/`, `output/02_Pfizer_.../` — with
everything for that job inside.

## What one job gets you — four things, not one

Everything lands in `output/01_Company_Role/`:

| | |
|---|---|
| **`research.md`** | What the company builds, what they actually use day to day, and where they're heading. This is what makes the resume feel written for them |
| **`resume.tex`** | Built only from things you've really done — then put through a tough recruiter review before you see it: match score out of 100, the keywords their screening software looks for, the three things a manager spots in ten seconds, and the fixes applied |
| **A different lead project each time** | Every resume leads with a different project of yours, angled at that employer. Ten companies, ten different lead projects |
| **`study-plan.md`** | What that company expects that you don't have yet — split into *before the first call*, *before the technical round*, and *first 90 days*, with one resource each |

**Why the study plan matters:** getting shortlisted takes three to six weeks. That waiting time is
yours. This tells you exactly what to learn for *that* company, so by the time they ring, you've
closed the gap.

**Nothing from the study plan goes on your resume.** Those are the things you don't have yet. The
moment you learn one — just say *"I finished the Docker one"* — it gets added to your profile, and
every resume from then on can use it.

**If nothing you've built fits a company,** you'll be told straight out, and given a small project
spec — their tools, their kind of problem, a few days' work — with the exact resume lines it earns
once it's real. Build it, say so, and that company's resume gets rebuilt with it. Their hiring runs
for weeks, so there's usually still time.

---

## Step 3 — Answer the questions it asks you

The AI only knows what's in `context/`. When a job needs something it can't find there, it stops and
asks rather than making it up:

> ⚠️ **NOT IN YOUR CONTEXT — did you forget to add it?**

Every one of those goes into **[context/QUESTIONS-FOR-YOU.md](context/QUESTIONS-FOR-YOU.md)** so they
don't scroll away. Answer them when you get a chance — **one answer often lifts several job matches
at once**, because the same requirement shows up across many ads.

---

## Getting a PDF

Say: **"turn resume 3 into a PDF"** and the AI walks you through it click by click. The simplest
route is [overleaf.com](https://overleaf.com) — free, paste the file, press one button. Don't want
anything technical at all? Say **"give me a plain Word-style resume instead"**.

---

## The rules the AI follows, so you can trust the output

- **It never invents anything.** No employer, date, number, tool, or certificate that isn't in your `context/`
- **It never puts something you're still learning on a resume** — in any form, however hedged
- **It never calls coursework a job**, or a college project professional experience
- **It tells you the gaps** rather than papering over them, and gives you an honest answer for each

---

That's the whole system. You fill `context/`, you ask, it works.
