#!/usr/bin/env python3
"""
ats_check.py — keyword coverage of a tailored resume against the job description.

  python3 system/scripts/ats_check.py --resume output/01_Acme_Analyst/resume.tex --jd output/01_Acme_Analyst/job-description.txt
  python3 system/scripts/ats_check.py --resume r.md --jd jd.txt --top 30 --json

What it does:
  * strips LaTeX commands / Markdown syntax so only readable resume text is compared
  * pulls candidate keywords out of the JD (single words and 2-3 word phrases), weighting
    terms that appear in requirement-like lines
  * reports coverage: missing, thin (once), covered (twice or more)

What it does NOT do: judge whether a claim is true. Only put a keyword in a resume if the
person can honestly back it. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

STOP = set("""
a about above after again against all am an and any are aren as at be because been before being
below between both but by can cannot could couldn did didn do does doesn doing don down during each
few for from further had hadn has hasn have haven having he her here hers herself him himself his
how i if in into is isn it its itself let me more most mustn my myself no nor not of off on once
only or other ought our ours ourselves out over own same shan she should shouldn so some such than
that the their theirs them themselves then there these they this those through to too under until
up very was wasn we were weren what when where which while who whom why with won would wouldn you
your yours yourself yourselves will shall may might must also across within without per via etc
 turn raw related field various join drive deliver ensure build building create make provide
 across based looking help support work works role roles day days team teams world class
 environment environments part write writing read reading get take taken bring

role job position company team work working experience years year candidate ideal strong good great
excellent ability able opportunity looking join help support ensure including include includes
required requirements responsibilities qualifications preferred plus nice desirable essential
knowledge understanding familiarity skills skill using use used well new using our you'll we're
""".split())

REQ_LINE = re.compile(
    r"(requir|must have|essential|responsib|qualifi|experience with|proficien|expertise|"
    r"familiar|knowledge of|degree in|skills|nice to have|preferred)", re.I)
# JD bullets are almost always requirements or responsibilities - weight them the same.
BULLET_LINE = re.compile(r"^\s*([-*\u2022\u00b7]|\d+[.)])\s+")


def line_weight(line: str) -> int:
    return 3 if (REQ_LINE.search(line) or BULLET_LINE.match(line)) else 1


def strip_latex(text: str) -> str:
    text = re.sub(r"(?m)^\s*%.*$", " ", text)          # comment lines
    text = re.sub(r"(?<!\\)%.*", " ", text)             # trailing comments
    text = re.sub(r"\\href\{[^}]*\}", " ", text)        # drop URLs, keep the label
    text = re.sub(r"\\[a-zA-Z@]+\s*(\[[^\]]*\])?", " ", text)
    return text.replace("{", " ").replace("}", " ").replace("\\", " ")


def strip_markdown(text: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[#*_`>|-]+", " ", text)
    return text


def read_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix == ".tex":
        return strip_latex(raw)
    if path.suffix in {".md", ".markdown"}:
        return strip_markdown(raw)
    return raw


def normalise(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9+#./\- ]+", " ", text)
    return re.sub(r"\s+", " ", text)


def words(text: str) -> list[str]:
    return [w.strip("-./") for w in normalise(text).split() if w.strip("-./")]


# Multi-word terms worth checking when they appear in a JD. Single words are found
# automatically; these are the phrases a naive tokeniser would lose.
KNOWN_PHRASES = """
machine learning|deep learning|data analysis|data analytics|data science|data cleaning|
data validation|data visualisation|data visualization|data engineering|data quality|
data modelling|data modeling|big data|statistical analysis|predictive modelling|
natural language processing|computer vision|feature engineering|model evaluation|
power bi|google cloud|amazon web services|microsoft azure|cloud computing|cloud platforms|
version control|source control|unit testing|test automation|continuous integration|
continuous delivery|software development|software engineering|object oriented|
web development|full stack|back end|front end|rest api|api design|
incident management|incident response|root cause|change management|service management|
technical support|customer support|problem solving|process improvement|quality assurance|
standard operating|operating procedures|attention to detail|stakeholder management|
project management|cross functional|risk assessment|risk analysis|fraud detection|
anomaly detection|content moderation|content review|policy enforcement|policy operations|
trust and safety|online safety|platform integrity|user safety|escalation management|
case management|decision making|network security|information security|access control|
identity management|penetration testing|vulnerability management|threat detection|
operating systems|computer networks|technical documentation|business intelligence|
requirements gathering|agile methodologies|scrum master|time management|team collaboration
""".replace("\n", "").split("|")
KNOWN_PHRASES = [p.strip() for p in KNOWN_PHRASES if p.strip()]

CAP_PHRASE = re.compile(r"\b([A-Z][A-Za-z0-9+#.]+(?:\s+[A-Z][A-Za-z0-9+#.]+){1,2})\b")


def jd_keywords(jd_text: str, top: int) -> list[tuple[str, int]]:
    """Rank JD terms by (occurrences x requirement-line weight).

    Single words are extracted automatically; multi-word terms come from a glossary of
    common phrases plus capitalised proper nouns found in the JD (e.g. "Power BI").
    """
    norm_lines = [(normalise(line), line_weight(line))
                  for line in jd_text.splitlines() if line.strip()]
    whole = " ".join(l for l, _ in norm_lines)

    scores: Counter[str] = Counter()

    # 1. single words
    for line, weight in norm_lines:
        for w in line.split():
            w = w.strip("-./")
            if len(w) > 2 and w not in STOP and not w.isdigit():
                scores[w] += weight

    # 2. glossary phrases actually present in this JD
    phrases = {p for p in KNOWN_PHRASES if p in whole}

    # 3. capitalised proper nouns from the raw text ("Power BI", "Google Cloud")
    for m in CAP_PHRASE.finditer(jd_text):
        cand = normalise(m.group(1)).strip()
        toks = cand.split()
        if 2 <= len(toks) <= 3 and all(t not in STOP for t in toks) and cand in whole:
            phrases.add(cand)

    for phrase in phrases:
        for line, weight in norm_lines:
            scores[phrase] += weight * line.count(phrase)

    # Phrases lead the list; they are the terms a resume most often misses.
    ranked_phrases = sorted(((k, v) for k, v in scores.items() if " " in k and v >= 2),
                            key=lambda kv: -kv[1])
    ranked_words = sorted(((k, v) for k, v in scores.items() if " " not in k and v >= 3),
                          key=lambda kv: -kv[1])

    phrase_slots = min(len(ranked_phrases), max(6, top // 2))
    kept = ranked_phrases[:phrase_slots]
    covered_by_phrase = {t for k, _ in kept for t in k.split()}
    for k, v in ranked_words:
        if len(kept) >= top:
            break
        # a word already carried by a kept phrase is only worth listing on its own if
        # the JD uses it a lot outside that phrase
        if k in covered_by_phrase and v < 4:
            continue
        kept.append((k, v))
    return kept[:top]


def count_in(resume_norm: str, term: str) -> int:
    return len(re.findall(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", resume_norm))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--resume", required=True)
    ap.add_argument("--jd", required=True)
    ap.add_argument("--top", type=int, default=25, help="how many JD keywords to check (default 25)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    resume_p, jd_p = Path(args.resume), Path(args.jd)
    for p in (resume_p, jd_p):
        if not p.exists():
            print(f"error: {p} not found", file=sys.stderr)
            return 2

    resume_norm = normalise(read_text(resume_p))
    keywords = jd_keywords(read_text(jd_p), args.top)

    rows = [{"term": t, "weight": w, "count": count_in(resume_norm, t)} for t, w in keywords]
    missing = [r for r in rows if r["count"] == 0]
    thin = [r for r in rows if r["count"] == 1]
    covered = [r for r in rows if r["count"] >= 2]
    score = round(100 * (len(covered) + 0.5 * len(thin)) / max(len(rows), 1))

    if args.json:
        print(json.dumps({"score": score, "rows": rows}, indent=2))
        return 0

    print(f"\nATS keyword check — {resume_p.name} vs {jd_p.name}")
    print(f"Coverage score: {score}%   "
          f"(covered {len(covered)} · thin {len(thin)} · missing {len(missing)} of {len(rows)})\n")

    def block(title: str, items: list[dict], hint: str):
        if not items:
            return
        print(f"{title}")
        for r in sorted(items, key=lambda r: -r["weight"]):
            print(f"  {r['count']}×  {r['term']}   (JD weight {r['weight']})")
        print(f"  → {hint}\n")

    block("MISSING — not in the resume at all:", missing,
          "Add each one you can honestly claim, in the section where it is true. "
          "If you cannot claim it, it is a gap: name it in the match assessment, do not add it.")
    block("THIN — appears once:", thin,
          "Aim for two mentions in different sections (e.g. Summary + Experience).")
    block("COVERED — twice or more:", covered, "Nothing to do.")

    print("Reminder: a keyword only belongs here if the person can defend it in an interview.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
