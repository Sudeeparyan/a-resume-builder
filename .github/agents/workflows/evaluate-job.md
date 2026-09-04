---
description: "Score one opportunity before investing effort — go/no-go in about five minutes."
---

# Workflow: evaluate a job

A short, standalone version of step 1 of `.github/agents/workflows/apply-to-job.md`, for triaging a pile of links.

1. Read `system/modes/_shared.md` (scoring) and `system/modes/_profile.md` (overrides).
2. Run `system/modes/evaluate.md` on the JD → blocks A–F.
3. Compute the priority score.
4. Output exactly three things:
   - **Score** and the track it belongs to
   - **The one reason** it scores that way
   - **Verdict:** apply now / apply if <condition> / skip because <reason>
5. Record skips in the tracker with the reason. An unrecorded skip gets re-evaluated next week and
   wastes the same five minutes again.

Batch mode: given 10–20 links, produce a single ranked table and only expand blocks A–F for the
top three.
