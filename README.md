# Annie's resume builder

A local job-search and resume workspace for **Annie Prasanna Manoharan**, United States only.

It finds entry-level data, ML/AI, software and embedded/test roles; drops any posting that refuses visa sponsorship or requires citizenship or a clearance (and shows the exact sentence, so a wrong call can be undone); never lets her apply to the same role twice; and builds one-page resumes that use only facts from her own files, each with a study plan for the interview weeks.

## Start

Double-click **Start Dashboard.command**. It sets itself up on first run and opens the dashboard at http://127.0.0.1:8010 (port 8000 on this Mac is a different person's dashboard; Annie's never uses it) (Dashboard · Daily Search · Resume Studio · Profile · Agents · Settings).

Or ask Claude in this folder: "find me jobs", paste a job description, or run `/hunt 10`.

## Folders

```text
career-dashboard/   the app: React dashboard, FastAPI backend, agents, validators, tests
  data/context/       Annie's own files (01–09, her 14 resume PDFs), the evidence registry, open questions
  data/output/        SUMMARY.md (the front page) and one folder per application
daily-job-search/   daily-run helpers, the PDF runtime wrapper, delivered-posting history
backup/             the workspace before the 18 Sep 2026 port (reference only)
.claude/            Claude skills and the /hunt command
```

Details: [career-dashboard/README.md](career-dashboard/README.md). Health check: double-click **Check Workspace.command**.
