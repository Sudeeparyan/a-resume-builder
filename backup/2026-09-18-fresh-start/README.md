# 2026-09-18-fresh-start

Snapshot taken before the job list was cleared for a new search.
`career.db` is a consistent SQLite backup of the whole database at that
moment; the projections beside it are the readable copies from the same
time. `applications/` holds the prepared resume folders that were moved
out of data/output/applications/.

Rows that were cleared:

- posting_identities: 4
- jobs: 2
- companies: 2

Application folders moved: 2

To go back, stop the dashboard, copy `career.db` over data/career.db and
move `applications/` back to data/output/applications/, then run
`backend/scripts/workspace.py export`.

Kept on purpose: reapply_history (every cleared company and role, for the
never-re-apply rules), excluded_postings and signature_assignments.
