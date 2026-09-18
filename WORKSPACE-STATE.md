# Career workspace state

Updated 18 September 2026.

## Where things stand

- **Port complete (18 Sep).** The workspace now runs the newer career-dashboard app (six tabs, agents, Resume Studio), rebuilt around Annie: US only, the sponsorship gate, never-re-apply rules, one-page US Letter resumes, a signature project per company, and study plans. The old `system/`, `dashboard/`, `output/`, root docs and agent files are in `backup/2026-09-18-pre-port/`.
- **Jobs:** 2, both `prepared`, neither applied. Carried over from the old tracker and re-saved through the gate:

  | Employer — role | Tier | Signature project | Watch-outs |
  |---|---|---|---|
  | University of Southern California — Research Engineer (CIC, neuroimaging ML), Los Angeles | S (cap-exempt, .edu) | MiGa (`PROJ-P02-MIGA`) | Draft needs research, evidence map and review |
  | Databricks — AI Engineer, FDE | B (459 H-1B approvals 2021–23) | IoT streaming platform (`PROJ-P01-IOT`) | The posting says it is **not for entry-level applicants**; decide whether to apply |

  Both drafts were rebuilt as one page. The old PDFs stay in the backup and must not be sent: the Databricks one names Medtronic for the ~94% figure and prints a leaked "see Q4" note.
- **Excluded postings:** none yet.
- **Open questions** (`career-dashboard/data/context/QUESTIONS-FOR-YOU.md`): Q3 publication details (title, venue, year, author position), whether the 94% was measured, whether she is still at InsOps, city (Q5), salary (Q6), the work-authorization line (Q10), LinkedIn (Q11).
- **Gmail:** not connected. Sync needs Codex signed in on this Mac; optional.

## Next action

Open the dashboard, run **Daily Search → Find suitable jobs** with *Tracked career pages* (no AI cost), and review the tier-ordered list. Or say "give me 10 companies" / `/hunt 10` in Claude.

## Checks

`./Check Workspace.command` runs the backend tests, the workspace and layout validators, the React build and the component tests.
