# LaTeX / Overleaf guide

These bases are a hardened version of the popular one-page "Jake" resume layout: compact, single
column, ATS-parseable. Two bases, same preamble and macros, so a resume can switch between them
without reformatting:

- **`resume-track-a.tex`** — experience-forward (Summary → Education → Experience → Projects → Skills
  → Publications → Achievements → Certifications). Use when there's real employment to lead with.
- **`resume-track-b.tex`** — education-forward (Summary → Education *with modules* → Projects →
  Experience → Skills → Certifications → Achievements). Use for students / graduates / career changers.
- **`cover-letter.tex`** — one-page cover letter (Pain → Agitate → Solution → Close).

A filled, compile-ready sample lives in [`system/examples/dublin-data-analyst/resume.tex`](../../examples/dublin-data-analyst/resume.tex).

## Compiling on Overleaf (no local install needed)

1. Go to **overleaf.com** → New Project → Blank Project.
2. Paste the whole `.tex` file in, replacing the default content.
3. Set the compiler to **pdfLaTeX** (Menu → Compiler). The preamble is tuned for pdfLaTeX.
4. **Recompile.** Download the PDF and rename it `Firstname_Lastname_RoleTitle.pdf`.

No LaTeX locally? That's the expected path — everything here is written to compile on Overleaf
as-is. `system/scripts/build_pdf.sh` is only for people who *do* have a local TeX toolchain.

## The rules that prevent the usual alignment / page problems

1. **Never touch the preamble** — document class, margins, and the `\newcommand` definitions
   (`\job`, `\project`, `\resumeSubheading`, `\sectioncontent`, `\ul`). All the spacing is tuned
   there. Only edit between `\begin{document}` and `\end{document}`.
2. **Delete unused blocks entirely.** An empty `\section` or a stray `\item` with nothing after it
   causes "There's no line here to end". If a section is empty, remove the whole section.
3. **Never leave a `{{TOKEN}}`** in a sent resume — it means a fact wasn't filled.
4. **Escape these characters in your content:** `%` → `\%`, `&` → `\&`, `_` → `\_`, `#` → `\#`,
   `$` → `\$`. (e.g. `40\%`, `R\&D`.) An unescaped `%` silently eats the rest of the line — a
   very common cause of "half my bullet disappeared".
5. **Keep `\pdfgentounicode=1` and the `glyphtounicode` line** — they make the PDF text extractable
   by ATS parsers. Removing them is how a resume becomes an unreadable image to a screener.
6. **Every `\href{url}{text}` needs a real url.** Delete any link the candidate doesn't have rather
   than leaving `\href{}{...}`.

## Fixing a page that overflows (1½ pages, or a lonely last line)

Fix in this order — never shrink the font below the base's `10.5pt`:

1. Trim the **oldest** role to fewer bullets; recent roles keep 3–5, older ones 2.
2. Cut the least JD-relevant project bullet, then the least relevant project.
3. Tighten wording — one line per bullet; a bullet that wraps to a 2nd line for one word is wasteful.
4. Only then, nudge a `\vspace{...}` down slightly (they're already tuned; small changes only).

Target: a graduate CV = **one full page**; an experienced CV = **two pages, ~95% of page 2 filled**.
Irish market convention (see `system/config/regions.yml → cv_conventions`): no photo, no date of birth,
state right-to-work briefly, include LinkedIn.

## Sanity-check before sending

`python system/scripts/../` isn't required, but a quick self-check: search the file for `{{`, for a stray
unescaped `%`, and confirm every `\begin{...}` has a matching `\end{...}`. Then compile once on
Overleaf and read the PDF end to end.
