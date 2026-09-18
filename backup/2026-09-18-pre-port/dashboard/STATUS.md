# Status — built overnight, 5 September 2026

## Start it

```
python dashboard/run.py
```

Opens at http://127.0.0.1:8000. No API key needed to try it.

---

## What works, verified end to end

| | Verified by |
|---|---|
| Both tabs render and the app serves from one process | live server, HTTP 200 |
| Scan finds ~1,100 real openings from 5 sources in under a minute | live run, 52s |
| Sponsorship gate with S/A/B/C tiers and verbatim triggering sentences | live run + 12 tests |
| Never-re-apply, 21/90/180-day rules | live run + tests |
| Apply links checked; dead ones dropped | live run, 3 dropped |
| Tier-first ordering (cap-exempt outranks a higher score) | test |
| Resume built from real facts, auto-fitted to exactly one page | 3 job types, all 1 page |
| Overleaf-style editor: live compile ~1.2s, errors on the right line | live API |
| **Fabrications blocked from shipping** | 4 planted lies, all caught |
| 83,624-employer sponsor index, 3ms lookups (was 239ms) | benchmark |
| Full suite | **58 tests passing** |

Run the checks yourself:

```
python -m pytest dashboard/tests -q
python dashboard/tests/probe_scan.py
python dashboard/tests/probe_build.py
python dashboard/tests/probe_honesty.py     # server must be running
```

---

## Bugs found and fixed while building

Worth knowing about, because several were in behaviour that looked fine:

1. **`is_us()` returned true for everything** — a `not in` that should have been
   `in`. Tokyo and Berlin roles were reaching the shortlist.
2. **No relevance filter at all** — hotel attendants and electricians were being
   scored against her profile.
3. **`Snowflake` passed the honesty check** because the word appears in
   `05-skills.md` *inside the do-not-claim list*. Honest gaps are now tracked
   separately from the corpus.
4. **Bullets were truncated mid-sentence.** `context/` wraps at ~100 columns and
   each source line was being read as its own bullet; `**` markers leaked into
   the PDF as a result.
5. **The LaTeX preamble was being cut to nothing.** The template's own comment
   block contains the literal text `\begin{document}`, so a substring search
   stopped there and produced a document with no `\documentclass`.
6. **Tectonic appeared to take 60s.** It takes 1.7s — my own code was pointing
   `TECTONIC_CACHE_DIR` at an empty directory, forcing a full bundle re-download.
7. **Three cap-exempt jobs were silently dropped** as "broken links". They were
   Indeed short-links, and Indeed blocks non-browser requests. Bot-blocking hosts
   are now `NEEDS_CHECK` — kept and labelled, never dropped.
8. **A scan overwrote `output/SUMMARY.md`**, and the importer then read its own
   output back, losing her hand-curated list. Now backed up before every write,
   and previous entries are carried forward. *(Her file was restored.)*
9. **`portals.yml` is stale** — Confluent is listed under Greenhouse and 404s
   there; they moved to Ashby, where they have 22 open roles. Board discovery now
   probes for the real one instead of trusting the config.
10. `track.py`'s `TODAY` is bound at import, so a long-running server would compute
    cooldowns against a stale date. Refreshed before every call.

---

## What is not done

Stated plainly rather than left to be discovered:

- **The LLM agents are written but have never run against the real API**, because
  there is no key on this machine. The provider layer, prompts, schemas and
  fallbacks are all in place and the no-key paths are tested; the first run with a
  real key should be treated as a first run.
- **The recruiter audit and study-plan agents are specified but not wired** into
  the build pipeline. Resume generation currently uses pure selection — which is
  the safe half. Tailored rewriting is the next piece.
- **The evaluation harness is designed, not built.** The deterministic half exists
  and runs (that is what the guards are); the golden set and LLM judge are not.
- The Claude Code CLI provider is implemented but untested — the CLI is not
  installed here.
- Adzuna and USAJobs are wired but off until credentials are added in Settings.
- Company research needs a key; without one, ads are read by keyword frequency.

---

## Expected timeline for a run

Measured on this machine, no key:

| Stage | Time |
|---|---|
| Sourcing ~1,100 jobs from 5 boards | 3s |
| Dedupe, filters, sponsorship gate, tracker | 2s |
| Link checking (polite, per-host delay) | 45–55s |
| Scoring, ranking, writing SUMMARY.md | <1s |
| **Total scan** | **~60s** |
| Build one resume (with page-fit loop) | 6–12s |
| Single compile in the editor | 1.2s (0.06s cached) |

With a key, add roughly 45–90s per company for research and 20s per job for the
prediction, run 3–4 at a time. A 10-job scan with full research lands around
**5–8 minutes**, shown live with a countdown.

---

## Two things to check first

1. **The ATS score on a generated resume is low (14%)** for the USC job, because
   that ad's text was scraped off a careers page and includes navigation. Ads
   coming straight from a company board score properly. Worth confirming against a
   real Greenhouse posting.
2. **The generated page runs slightly light** — about 2,900–3,200 characters
   against a 3,300 target. It is one page and honest, but denser than the fit loop
   currently manages would be better. Not a blocker; it shows as a "thin" warning.
