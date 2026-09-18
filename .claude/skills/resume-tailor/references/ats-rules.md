# ATS rules

What applicant tracking systems actually do to a resume, and how to survive it.

## How parsing fails

| Cause | Effect | Fix |
|-------|--------|-----|
| Multi-column layouts | Columns interleave into nonsense | One column, always |
| Text in headers/footers | Dropped entirely | Contact details in the body |
| Tables used for layout | Cells read out of order | Tables only for genuinely tabular content, or none |
| Images, icons, logos, photos | Ignored; sometimes break parsing | No images. Icons only as text glyphs |
| Text boxes / shapes | Dropped | Never |
| Non-standard section names | Section unrecognised, content unmapped | "Experience", not "Where I've Made an Impact" |
| Unusual date formats | Employment dates lost | `Mon YYYY -- Mon YYYY` everywhere |
| Fancy bullets / dingbats | Garbled characters | Standard bullets |
| Ligature-heavy PDFs | "fi"/"fl" merge, breaking keyword matching | The validator fails a PDF whose text is not extractable |

## Keyword placement

1. Each must-have keyword appears **at least twice**, in different sections — typically Technical
   Skills + Experience, or Skills + Projects. (Annie's resume has no Summary section.)
2. Use the JD's exact string at least once, where true: "Apache Airflow orchestration", not only "workflow scheduling".
3. Cover both forms of common pairs: "Machine Learning (ML)", "Standard Operating Procedures
   (SOPs)".
4. Front-load: parsers and humans both weight the first third of the document.
5. Never keyword-stuff, never use white text, never add a hidden keyword block. Modern ATS flags it
   and a human reads the resume afterwards anyway.

## Section headings that parse reliably

`Education` · `Experience` · `Professional Experience` · `Projects` ·
`Technical Skills` · `Skills` · `Certifications` · `Publications` · `Awards` · `Languages`

Annie's contract fixes four: Education, Technical Skills, Professional Experience, Projects. Certifications and Publications stay off until something real is on record.

## Contact block

Name on its own line, then a single line of phone · email · portfolio · GitHub. Annie's resumes print no city (Q5 open) and no LinkedIn (none on record).

## File format

- Submit **PDF** unless the portal explicitly asks for .docx. PDFs generated from LaTeX parse well
  when `glyphtounicode` is enabled.
- The folder carries the identity (`Annie_Manoharan_<Company>_<NN>`); the file inside is always `resume.pdf`. Rename a copy to `Annie_Manoharan_Resume.pdf` when a portal shows the filename.
- Keep it under 1 MB.

## Verify before sending

```bash
career-dashboard/backend/.venv/bin/python career-dashboard/backend/scripts/workspace.py score --job-id JOB_ID
```

Then the manual check that catches most parser problems: copy the text out of the built PDF into a
plain text editor. If the order is wrong or content is missing there, the ATS sees the same thing.
