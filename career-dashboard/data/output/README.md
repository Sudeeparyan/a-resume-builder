# Generated resumes

`SUMMARY.md` is the front page Annie reads: last run, her resumes (tier, status, apply link), the pipeline with days quiet, companies found without a resume yet, everything excluded with the sentence that triggered it, and what to study this week. It is regenerated from `data/career.db` after every change.

`base/` holds the base one-page resume (`Annie_Manoharan_Resume.pdf`), its QA report and its page preview.

`applications/Annie_Manoharan_<Company>_<NN>/` holds one application each: the JD snapshot, evaluation, company research, study plan, evidence map, `resume.tex`, `resume.pdf`, `resume-preview/page-01.png` and `qa.json`. Studio previews and fits are kept beside them as `preview-<revision>/`.

`batches/` is the home for batch runs.

These files are results, never sources of candidate claims. A PDF without a current passing QA and a recorded visual review is still a draft.
