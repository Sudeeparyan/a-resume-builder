#!/usr/bin/env bash
# Build a PDF from a .tex or .md resume.
#   bash system/scripts/build_pdf.sh output/01_Acme_Data_Analyst/resume.tex
#   bash system/scripts/build_pdf.sh output/01_Acme_Data_Analyst/resume.md
#   bash system/scripts/build_pdf.sh --docx output/01_Acme_Data_Analyst/resume.md
# Engines are tried in order and the first available one wins.
set -euo pipefail

WANT_DOCX=0
if [[ "${1:-}" == "--docx" ]]; then WANT_DOCX=1; shift; fi

SRC="${1:-}"
if [[ -z "$SRC" ]]; then
  echo "usage: bash system/scripts/build_pdf.sh [--docx] <file.tex|file.md>" >&2
  exit 2
fi
[[ -f "$SRC" ]] || { echo "error: no such file: $SRC" >&2; exit 2; }

DIR="$(cd "$(dirname "$SRC")" && pwd)"
BASE="$(basename "${SRC%.*}")"
EXT="${SRC##*.}"
OUT="$DIR/$BASE.pdf"

# Refuse to build a resume that still has unfilled placeholders.
if grep -q '{{[A-Z_0-9]\+}}' "$SRC"; then
  echo "⚠  $SRC still contains unfilled {{PLACEHOLDERS}}:" >&2
  grep -o '{{[A-Z_0-9]\+}}' "$SRC" | sort -u | sed 's/^/     /' >&2
  echo "   Fill them (or delete the block) before building. Building anyway is almost never right." >&2
  exit 1
fi

# Refuse to build a resume still carrying [FILL IN: …] markers — those are numbers only the
# candidate can supply, left deliberately empty by the recruiter audit rather than guessed.
if grep -qi '\[FILL IN' "$SRC"; then
  echo "⚠  $SRC still contains [FILL IN] markers — real numbers are missing:" >&2
  grep -oi '\[FILL IN[^]]*\]' "$SRC" | sort -u | sed 's/^/     /' >&2
  echo "   Ask the candidate for these figures, write them into system/profile/master-profile.md, and" >&2
  echo "   regenerate. Never guess one — a fabricated metric fails at the first interview." >&2
  exit 1
fi

have() { command -v "$1" >/dev/null 2>&1; }

case "$EXT" in
  tex)
    if have tectonic; then
      echo "→ tectonic"
      tectonic --outdir "$DIR" "$SRC"
    elif have latexmk; then
      echo "→ latexmk"
      latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir="$DIR" "$SRC" >/dev/null
      latexmk -c -outdir="$DIR" "$SRC" >/dev/null 2>&1 || true
    elif have pdflatex; then
      echo "→ pdflatex (two passes)"
      for _ in 1 2; do
        (cd "$DIR" && pdflatex -interaction=nonstopmode -halt-on-error "$(basename "$SRC")" >/dev/null)
      done
      (cd "$DIR" && rm -f "$BASE".{aux,log,out,fls,fdb_latexmk})
    else
      cat >&2 <<'MSG'
No LaTeX engine found. Options:
  1. Paste the .tex into https://overleaf.com and compile there (nothing to install)
  2. Install one:
       macOS         brew install --cask mactex-no-gui     (or: brew install tectonic)
       Debian/Ubuntu sudo apt-get install texlive-latex-extra latexmk
       Windows       install MiKTeX, or use Overleaf
MSG
      exit 1
    fi
    ;;

  md)
    have pandoc || { echo "pandoc not found. Install it (brew/apt install pandoc) or use the LaTeX path." >&2; exit 1; }
    if [[ $WANT_DOCX -eq 1 ]]; then
      OUT="$DIR/$BASE.docx"
      pandoc "$SRC" -o "$OUT" --from=markdown+smart
    else
      ENGINE_ARGS=()
      if have pdflatex || have xelatex || have tectonic; then
        ENGINE_ARGS=(-V geometry:margin=0.7in -V fontsize=10pt)
      else
        echo "pandoc has no PDF engine available; producing .docx instead." >&2
        OUT="$DIR/$BASE.docx"
        pandoc "$SRC" -o "$OUT"; echo "✓ $OUT"; exit 0
      fi
      if ! pandoc "$SRC" -o "$OUT" "${ENGINE_ARGS[@]}" 2>/tmp/pandoc-err.$$; then
        echo "  pdflatex path failed, retrying with xelatex..." >&2
        if ! pandoc "$SRC" -o "$OUT" --pdf-engine=xelatex "${ENGINE_ARGS[@]}" 2>>/tmp/pandoc-err.$$; then
          echo "  PDF engines unavailable or missing packages; writing .docx instead:" >&2
          sed -n '1,6p' /tmp/pandoc-err.$$ >&2
          OUT="$DIR/$BASE.docx"
          pandoc "$SRC" -o "$OUT"
        fi
      fi
      rm -f /tmp/pandoc-err.$$
    fi
    ;;

  *)
    echo "error: expected a .tex or .md file, got .$EXT" >&2; exit 2;;
esac

echo "✓ $OUT"
echo "  Before sending: open it, read it end to end, and rename to Firstname_Lastname_RoleTitle.pdf"
