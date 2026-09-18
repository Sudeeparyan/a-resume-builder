# Daily job search

Follow `DAILY_BRIEF.md` for discovery, the sponsorship gate, eligibility, evidence and release checks. From the repo root:

```sh
career-dashboard/backend/.venv/bin/python daily-job-search/search.py start
career-dashboard/backend/.venv/bin/python daily-job-search/search.py add --file POSTING.json
career-dashboard/backend/.venv/bin/python daily-job-search/search.py list
```

Posting JSON fields: company, title, location, url, description (the full JD). `add` runs the same path as the dashboard: a posting that refuses sponsorship or requires citizenship/clearance is recorded under Excluded roles with its sentence and is not linked to the run; a role Annie already saw, or a company that rejected her within 180 days, is reported as blocked. `search.py link JOB_ID` attaches an existing opportunity to today (`--date YYYY-MM-DD` for another run). `search.py notes --file NOTES.md` saves search coverage.

The dashboard offers the same daily controls. Resumes live in the dashboard's application folders. Dated `YYYY-MM-DD/run.json` files are generated database views.

`history.csv` keeps previously delivered postings for deduplication. `with_resume_runtime.py` wraps Tectonic and the PDF tools with local caches; the dashboard launcher uses it.
