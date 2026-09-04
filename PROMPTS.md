# The exact prompts to type

Copy one of these, paste it into Claude Code (or Copilot / Codex) opened in this folder, press
enter. That's the whole job.

You don't need to remember any of it — **`/hunt` alone does the main one.**

---

## THE ONE YOU'LL USE EVERY WEEK

```
/hunt
```

That's it. It runs the full loop:

1. Reads everything you've told it about yourself
2. Checks what you've already applied to and been rejected from — those never come back
3. Searches US jobs across all four of your tracks
4. Pulls the full job description for each one
5. **Throws out anything that says it won't sponsor**, and anything needing citizenship or a
   security clearance
6. Ranks what's left, cap-exempt employers first
7. Picks the top 10 and writes a tailored one-page resume for each
8. Builds all 10 PDFs and checks each is exactly one page
9. Gives you the `.tex` files too, so you can edit any of them in Overleaf
10. Records everything so next week's run doesn't repeat itself

**You get:** 10 folders in `output/`, each named `Annie_Manoharan_<Company>_<NN>`, each holding a
`.pdf` to send and a `.tex` to edit. Plus `output/SUMMARY.md` — the one page that tells you what
happened and where to apply.

### Same thing, in plain words (if you'd rather not use a slash command)

```
Find me 10 US jobs that match my profile, skip any that say they won't sponsor,
and build me a tailored one-page resume for each — LaTeX and PDF.
```

### Variations

```
/hunt 5
```
Five instead of ten.

```
/hunt data engineer
```
Only Data Engineer roles.

```
/hunt cap-exempt
```
Only universities, national labs and nonprofit research — **no H-1B lottery, they file
year-round.** Worth running every single week; it's your best structural advantage and almost
nobody competes there.

```
/hunt remote
```
Remote-only.

---

## ONE SPECIFIC JOB YOU FOUND YOURSELF

Paste the link, or the whole job description text:

```
https://boards.greenhouse.io/company/jobs/1234567
```

You don't need to write anything around it. A job link or a pasted description automatically
triggers the full pipeline: company research → sponsorship check → tailored one-page resume →
recruiter audit → PDF → what to study before they call.

If you want to be explicit:

```
Tailor my resume for this job and tell me honestly whether it's worth applying:
<paste the job description>
```

---

## AFTER YOU HEAR BACK

The whole point of this is that you never apply to the same place twice. Just tell it what
happened, in plain words:

```
I got rejected by Stripe for the Data Engineer role
```

```
I applied to Medtronic today
```

```
Databricks moved me to a phone screen
```

```
Boston Scientific ghosted me
```

It updates the tracker. Rejected companies disappear from your searches for 180 days, and that
exact role never comes back at all.

### Check before you apply anywhere manually

```
Have I already applied to Snowflake?
```

### See where everything stands

```
Show me my pipeline — what's out, what's gone quiet, what needs a follow-up
```

---

## CHANGING A RESUME

```
Make the Stripe resume lead with the streaming project instead
```

```
The Medtronic resume is too technical — make it read for a hiring manager, not an engineer
```

```
Rebuild resume 3 as one page, it's spilling over
```

You can also just open the `.tex` file in Overleaf and edit it yourself — that's why you get both.
Upload the `.tex`, hit Recompile, done. Nothing unusual is needed to compile it.

---

## INTERVIEW PREP

```
I have an interview at Confluent on Thursday — prep me
```

```
What will they ask me about the Flink project, and what are the answers I don't have yet?
```

```
How do I answer the sponsorship question without hurting myself?
```

---

## KEEPING IT ACCURATE

Every one of these makes **all future resumes** better, permanently:

```
I finished the AWS Data Engineer certification
```

```
I built a dbt project — here's what it does: <describe it>
```

```
My LinkedIn is linkedin.com/in/...
```

```
I'd only move to Austin or stay remote
```

```
My salary floor is 95k
```

### The four questions worth answering first

Open `context/QUESTIONS-FOR-YOU.md` — or just say:

```
Ask me the questions that are blocking my resumes
```

Four of them currently limit what your resume is allowed to say:

1. **Soliton dates** — your resumes disagree. Eleven say one 2-year role; three say internship
   plus one year as Project Engineer. Until you settle it, no resume can state how many years of
   experience you have.
2. **InsOps title** — "Data Engineering Intern" or "Data Science Intern"? And are you still there?
3. **Publications** — the config claims an ICCV 2025 paper, but **none of your 14 resumes mentions
   it.** If it's real it's your single strongest asset and it opens the O-1 route, which has no
   lottery. If it isn't, it gets deleted so it can't leak onto a resume.
4. **The ~94% figure** — Medtronic or Dräger?

---

## MAINTENANCE (rarely needed)

```
Refresh the H-1B sponsor data
```
Re-downloads the USCIS employer data. Worth doing every few months.

```
Check my job links are still live
```

```
Run a health check on the workspace
```

---

## WHAT IT WILL NEVER DO

So you can trust the output:

- **Never show you a company that says it won't sponsor.** That's a hard rule, not a preference.
- **Never show you a role needing US citizenship, a security clearance, or ITAR status** — those
  can't hire you no matter how the interview goes.
- **Never show you a company that already rejected you** (180 days), or the same role twice.
- **Never invent a job, a link, a company, or a metric.**
- **Never put a skill on your resume that you don't have** — those go in the study plan instead.
- **Never claim a publication or a years-of-experience total** until you've confirmed them.
- **Never send a two-page resume.** The build fails if it spills.

### One thing it deliberately *does* do

**It shows you companies with no H-1B sponsorship record.** Most employers never say anything
about sponsorship, and most never appear in the government data — but plenty of them sponsor once
you've cleared the interviews. Filtering those out would throw away most of your real chances.

Only an explicit *"we don't sponsor"* gets a company removed.
