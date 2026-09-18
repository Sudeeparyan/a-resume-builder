# system/ — the machinery

**Nothing in here needs your attention.** It's the AI's instruction manual and working parts. You
only ever touch [`context/`](../context/); everything you get back appears in
[`output/`](../output/).

Left here for reference only:

| Path | What it is |
|------|-----------|
| `config/profile.yml` | Your identity, tracks and targets — filled in from `context/` |
| `config/regions.yml` | The the United States market pack: job boards, hubs, work-permit routes, CV conventions |
| `config/portals.yml` | Career pages to check and the saved searches to run |
| `modes/_shared.md` | The rules every task follows: scoring, honesty, ATS writing |
| `modes/_profile.md` | Your personal overrides — these beat the shared rules |
| `modes/scan · evaluate · deep · batch · upskill` | How each kind of request is carried out |
| `profile/` | The tidied, structured copy of your `context/`, built by the intake step |
| `data/` | Applied-companies list, company notes, signature-project registry, scan history |
| `templates/` | The LaTeX and Markdown bases every resume is built on |
| `scripts/` | `doctor.py` (health check), `init_profile.py`, `ats_check.py`, `build_pdf.sh` |
| `examples/` | A fictional worked example, for reference |
| `SETUP.md` · `DATA_CONTRACT.md` · `PLACEHOLDERS.md` | Setup guide, what's yours vs. updatable, token list |

## One thing worth knowing

`profile/` here is a **copy** of your `context/`, tidied so the AI can work fast. `context/` is the
original and always wins. If you change something in `context/`, just say *"I've updated my context"*
and this copy gets rebuilt.

That also means: **everything in `system/profile/`, `system/data/` and `output/` can be regenerated.
`context/` cannot.** If you back up one folder, back up that one.
