# Output formats

## Choosing a format

| Situation | Format |
|-----------|--------|
| Default | LaTeX → PDF (`system/templates/latex/`) |
| No LaTeX toolchain and no Overleaf | Markdown → PDF via pandoc (`system/templates/markdown/`) |
| Portal demands .docx | Markdown → docx via pandoc, then check the layout by eye |
| Portal has a paste-the-text box | Plain text from the built PDF, sections in order |

## Building

```bash
bash system/scripts/build_pdf.sh output/01_Acme_Data_Analyst/resume.tex     # LaTeX → PDF
bash system/scripts/build_pdf.sh output/01_Acme_Data_Analyst/resume.md      # Markdown → PDF
bash system/scripts/build_pdf.sh --docx output/01_Acme_Data_Analyst/resume.md
```

The script tries `tectonic`, then `latexmk`, then `pdflatex`, then `pandoc`; it prints the
install hint for whichever is missing and always leaves the source untouched. With no toolchain
available, paste the `.tex` into <https://overleaf.com> and compile there — that path needs nothing
installed.

## Naming

| Artefact | Path |
|----------|------|
| Resume source | `output/NN_Company_Role/resume.tex` |
| Built PDF for the portal | `Firstname_Lastname_RoleTitle.pdf` |
| Cover letter | `output/NN_Company_Role/cover-letter.md` |
| The JD you tailored against | `output/NN_Company_Role/job-description.txt` |
| Company research | `output/NN_Company_Role/research.md` |

`NN` is the zero-padded application number, shared across all four files for one application.

## LaTeX rules

- Never change the document class, margins, or custom command definitions in the base.
- Escape `% & _ # $` in content. `%` in a bullet must be `\%` or the rest of the line disappears.
- Keep `\input{glyphtounicode}` and `\pdfgentounicode=1` — they are what makes the PDF's text
  extractable by ATS parsers.
- Compile before sending. An uncompiled `.tex` is not a deliverable.
