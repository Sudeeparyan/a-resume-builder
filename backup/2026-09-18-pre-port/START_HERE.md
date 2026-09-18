# Start here

This folder finds you US jobs and writes the resumes for them.

You never need to open anything under `system/` or `dashboard/`. You only ever touch one
folder: `context/`.

| Folder | What it is |
|--------|------------|
| **`context/`** | **Yours.** Everything about you. The only folder you ever edit. |
| `output/` | What you get back — resumes, PDFs, and `SUMMARY.md` |
| `system/` | The machinery. Ignore it. |
| `dashboard/` | Optional local web app. Ignore it unless you want the live editor. |

Every file, explained on one page: **[STRUCTURE.md](STRUCTURE.md)**.

---

## Type this

```
/hunt
```

You'll get back **10 US jobs you can actually take** and **10 tailored one-page resumes** —
each as a PDF to send and a `.tex` file you can edit in Overleaf.

Everything else you might want to say is in **[PROMPTS.md](PROMPTS.md)**.

---

## What it will never show you

- Any company whose posting says **it won't sponsor**
- Any role needing **US citizenship, a security clearance, or ITAR status** — those can't hire
  you regardless of how the interview goes
- Any company that **already rejected you** (for 180 days), or the same role twice

## What it deliberately *does* show you

Companies that say **nothing** about sponsorship — which is most of them. Many will sponsor once
you've cleared the interviews, and filtering them out would throw away most of your real chances.

Roles are ranked best-first:

| Tier | Meaning |
|---|---|
| **S** | **Cap-exempt** — universities, national labs, nonprofit research, academic medical centers. **No H-1B lottery, they file any time of year.** |
| **A** | The posting explicitly offers sponsorship |
| **B** | The company has sponsored before; the posting doesn't mention it |
| **C** | No information either way — the normal case, still worth applying |

**Run `/hunt cap-exempt` every week.** The FY2026 H-1B lottery was about 339,000 registrations for
85,000 places. Cap-exempt employers skip it entirely, you already work at one, and hardly anyone
competes there.

---

## After you hear back, just say so

```
I got rejected by Stripe
I applied to Medtronic today
Confluent gave me a phone screen
```

That's the whole tracking system. Rejected companies stop appearing. You'll never send the same
company the same resume twice.

---

## Where to look afterwards

- **`output/SUMMARY.md`** — the one page. What was found, what was built, what to do next.
- **`output/Annie_Manoharan_<Company>_<NN>/`** — one folder per application:
  - `resume.pdf` — send this
  - `resume.tex` — edit this in Overleaf if you want to change something
  - `job-description.txt` — what you were matched against
  - `audit.md` — which experience and project were chosen, and why
  - `research.md` — what the company actually does *(needs an AI key)*
  - `study-plan.md` — what to learn before they call *(needs an AI key)*

## Answer the questions when you can

**`context/QUESTIONS-FOR-YOU.md`** holds things I couldn't work out from your 14 resumes. Or just
say:

```
Ask me the questions that are blocking my resumes
```

Four of them limit what your resume is allowed to claim right now — your Soliton dates, your
InsOps title, whether the ICCV publication is real, and which client the ~94% figure belongs to.
Answer them once and every future resume improves.

---

## The one rule worth knowing

**A skill you're studying never goes on a resume.** Not as "familiar with", not as "exposure to".

The resume gets you shortlisted using only what you've already done. The study plan wins the
interview three to six weeks later. When you've genuinely learned something, tell me and it moves
across — and then every future resume picks it up automatically.
