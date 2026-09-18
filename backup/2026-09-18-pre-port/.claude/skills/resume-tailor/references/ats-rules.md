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
| Ligature-heavy PDFs | "fi"/"fl" merge, breaking keyword matching | `\input{glyphtounicode}` + `\pdfgentounicode=1` (already in the bases) |

## Keyword placement

1. Each must-have keyword appears **at least twice**, in different sections — typically Summary +
   Experience, or Skills + Projects.
2. Use the JD's exact string at least once: "CI/CD pipelines", not only "deployment automation".
3. Cover both forms of common pairs: "Machine Learning (ML)", "Standard Operating Procedures
   (SOPs)".
4. Front-load: parsers and humans both weight the first third of the document.
5. Never keyword-stuff, never use white text, never add a hidden keyword block. Modern ATS flags it
   and a human reads the resume afterwards anyway.

## Section headings that parse reliably

`Summary` · `Education` · `Experience` · `Professional Experience` · `Projects` ·
`Technical Skills` · `Skills` · `Certifications` · `Publications` · `Awards` · `Languages`

## Contact block

Name on its own line, then a single line of phone · email · location · links. City and country
only — full street addresses are not needed and can trigger location filters.

## File format

- Submit **PDF** unless the portal explicitly asks for .docx. PDFs generated from LaTeX parse well
  when `glyphtounicode` is enabled.
- Filename: `Firstname_Lastname_RoleTitle.pdf`. Never `resume_final_v3.pdf`.
- Keep it under 1 MB.

## Verify before sending

```bash
python3 system/scripts/ats_check.py --resume output/NN_Company_Role/resume.tex --jd output/NN_Company_Role/job-description.txt
```

Then the manual check that catches most parser problems: copy the text out of the built PDF into a
plain text editor. If the order is wrong or content is missing there, the ATS sees the same thing.
