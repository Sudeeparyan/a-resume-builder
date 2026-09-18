# Career workspace state

Updated 19 September 2026.

## Where things stand

- **Two dashboards live on this Mac.** Annie's opens at **http://127.0.0.1:8010** (tab title *Annie · Career Workspace*). Port 8000 is a different person's dashboard (*Chetan · Career Workspace*): nothing there is hers, and her launcher now refuses to open a browser on it. If a tab ever shows someone else's jobs, check the address bar: it must say **8010**.
- **Port complete (18 Sep).** The workspace runs the newer career-dashboard app (six tabs, agents, Resume Studio), rebuilt around Annie: US only, the sponsorship gate, never-re-apply rules, one-page US Letter resumes, a signature project per company, and study plans. The old `system/`, `dashboard/`, `output/`, root docs and agent files are in `backup/2026-09-18-pre-port/`.
- **Fresh start (18 Sep).** The earlier database (USC and Databricks rows, old folders) was snapshotted to `backup/2026-09-18-fresh-start/` and cleared. Two real US postings were then found through the tracked career pages (`data/config/portals.yml`), gated and prepared:

  | Employer — role | Tier | Signature project | Watch-outs |
  |---|---|---|---|
  | Snowflake — Software Engineer, Database Engineering (Menlo Park) | B (H-1B history) | Expense analytics (`PROJ-P06-EXPENSE`) | Company research found the same requisition marked **CLOSED** on Snowflake's own careers site on 18 Sep; the Ashby link could not be confirmed either way. Open the posting in a browser before applying. |
  | Snowflake — Software Engineer, Backend (Menlo Park) | B (H-1B history) | Expense analytics (`PROJ-P06-EXPENSE`) | Posting says 2+ years' software experience; research, match and study plan are in the folder. |

  Both resumes are one US Letter page (`data/output/applications/Annie_Manoharan_Snowflake_01`, `_02`), scored under `career-assessment-v3` (ATS readiness 95). Neither has been applied to.
- **Excluded postings:** 34, each with the sentence that triggered the sponsorship gate (Dashboard → *Excluded roles*).
- **Goals:** 30 applications a week, Monday to Saturday, from 18 Sep.
- **Open questions** (`career-dashboard/data/context/QUESTIONS-FOR-YOU.md`): Q3 publication details (title, venue, year, author position), whether the 94% was measured, whether she is still at InsOps, city (Q5), salary (Q6), the work-authorization line (Q10), LinkedIn (Q11).
- **Gmail:** not connected. Sync needs Codex signed in on this Mac; optional. The `email` agent must not be run from a shared sign-in.

## Next action

Double-click **Start Dashboard.command** (it opens 8010). In Resume Studio, pick a Snowflake role, read *Check match*, then apply through the posting link and mark it applied. Or run **Daily Search → Find suitable jobs** with *Tracked career pages* (no AI cost) for more roles.

## Checks

`./Check Workspace.command` runs the backend tests, the workspace and layout validators, the React build and the component tests.
