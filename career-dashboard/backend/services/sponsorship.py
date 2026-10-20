"""The sponsorship gate: the one hard exclusion in Annie's job search, then ranking.

    Posting explicitly WILL NOT sponsor          -> EXCLUDED, never shown
    Posting requires citizenship/clearance/ITAR  -> EXCLUDED, cannot be hired at all
    Posting says NOTHING about sponsorship       -> SHOW (most postings)
    Posting explicitly WILL sponsor              -> SHOW, ranked top

Tiers, all shown, best first:
    S cap-exempt employer (no lottery)  A says yes  B proven H-1B sponsor, silent posting
    C silent, no record (the normal case; never a negative)

Patterns live in data/config/sponsorship.yml. Every exclusion carries the exact
sentence that triggered it, so a wrong exclusion is visible and reversible.
H-1B history comes from data/sponsors/sponsors-uscis.csv (USCIS FY2021-2023),
indexed once into data/sponsors/index.db.

Standard library plus PyYAML only. `evaluate()` is the function callers use.
"""
from __future__ import annotations

import csv
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from backend.paths import CONFIG, DATA

RULES_PATH = CONFIG / "sponsorship.yml"
SPONSORS_DIR = DATA / "sponsors"
SPONSORS_CSV = SPONSORS_DIR / "sponsors-uscis.csv"
INDEX_DB = SPONSORS_DIR / "index.db"

TIER_RANK = {"S": 1, "A": 2, "B": 3, "C": 4, "EXCLUDED": 99}
TIER_LABEL = {
    "S": "Cap-exempt employer: files H-1B year-round, no lottery",
    "A": "Posting says it sponsors",
    "B": "Proven H-1B sponsor; posting is silent",
    "C": "Posting is silent and no H-1B record; still worth applying",
    "EXCLUDED": "Excluded by the posting's own words",
}

# Employer-name suffixes ignored when matching the USCIS index. Must stay identical
# to the refresh script that builds employer_key.
SUFFIXES = (
    "incorporated", "inc", "llc", "l.l.c", "ltd", "limited", "corp", "corporation",
    "company", "co", "plc", "gmbh", "llp", "lp", "pllc", "pc", "sa", "nv", "ag",
    "holdings", "group", "technologies", "technology", "labs", "laboratories",
    "solutions", "services", "systems", "usa", "us", "america", "international",
)


@dataclass
class Screen:
    verdict: str                 # KEEP | EXCLUDED
    reason: str                  # no_sponsorship | cannot_hire | explicit_sponsorship | silent
    reason_label: str
    sentence: str = ""           # the exact wording that decided it (exclusion or first positive hit)
    pattern: str = ""
    evidence: list[dict] = field(default_factory=list)
    everify: bool = False


@dataclass
class Verdict:
    tier: str                    # S | A | B | C | EXCLUDED
    screen: Screen
    cap_exempt: bool = False
    cap_exempt_reason: str = ""
    h1b_found: bool = False
    h1b_matched_name: str | None = None
    h1b_approvals: int = 0
    h1b_years: list[str] = field(default_factory=list)
    h1b_denials: int = 0
    everify: bool = False
    restored: bool = False       # Annie reviewed the exclusion sentence and restored the posting

    @property
    def excluded(self) -> bool:
        return self.tier == "EXCLUDED"

    @property
    def triggering_sentence(self) -> str:
        return self.screen.sentence if self.excluded else ""

    def label(self) -> str:
        if self.tier == "B" and self.h1b_approvals:
            years = ", ".join(self.h1b_years) if self.h1b_years else "recent years"
            return f"H-1B history: {self.h1b_approvals:,} approvals ({years}); posting is silent"
        if self.tier == "S" and self.cap_exempt_reason:
            return f"{TIER_LABEL['S']} ({self.cap_exempt_reason})"
        return TIER_LABEL[self.tier]

    def evidence_json(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "label": self.label(),
            "reason": self.screen.reason,
            "sentence": self.screen.sentence,
            "pattern": self.screen.pattern,
            "cap_exempt": self.cap_exempt,
            "cap_exempt_reason": self.cap_exempt_reason,
            "h1b_found": self.h1b_found,
            "h1b_matched_name": self.h1b_matched_name,
            "h1b_approvals": self.h1b_approvals,
            "h1b_years": self.h1b_years,
            "h1b_denials": self.h1b_denials,
            "everify": self.everify,
            "positive_evidence": self.screen.evidence,
            "restored": self.restored,
        }

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["excluded"] = self.excluded
        data["label"] = self.label()
        return data


def overridden(evidence: dict[str, Any] | None, verdict: "Verdict") -> bool:
    """True when Annie already restored this job after reviewing this exact exclusion sentence."""
    evidence = evidence or {}
    return bool(verdict.excluded and evidence.get("restored") and evidence.get("sentence") == verdict.screen.sentence)


# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------
# Broad Group 1 patterns retired on 2026-10-02. "now or in the future" alone matches the
# standard application question ("Will you now or in the future require sponsorship?"),
# and "no C2C" is about contractors, not visas; both hid postings open to Annie. They are
# skipped even if an older copy of sponsorship.yml still lists them.
RETIRED_PATTERNS = {
    r"now\s+or\s+in\s+the\s+future",
    r"no\s+(C2C|corp\s*to\s*corp|third[- ]party)",
}


def load_rules(path: str | None = None) -> dict[str, Any]:
    """Compiled gate rules; an edited sponsorship.yml takes effect without a restart."""
    target = Path(path) if path else RULES_PATH
    try:
        stamp = target.stat().st_mtime_ns
    except OSError:
        stamp = 0
    return _compile_rules(str(target), stamp)


@lru_cache(maxsize=8)
def _compile_rules(path: str, _stamp: int) -> dict[str, Any]:
    import yaml

    with Path(path).open(encoding="utf-8") as stream:
        cfg = yaml.safe_load(stream) or {}
    compiled: dict[str, Any] = {}
    for group in ("exclude_no_sponsorship", "exclude_cannot_hire", "positive_sponsorship",
                  "everify_signals", "do_not_exclude_on", "negation_guards", "ambiguous_sponsor_noun"):
        patterns = []
        for raw in cfg.get(group, []) or []:
            if group == "exclude_no_sponsorship" and raw in RETIRED_PATTERNS:
                continue
            try:
                patterns.append(re.compile(raw, re.IGNORECASE))
            except re.error:
                continue
        compiled[group] = patterns
    compiled["cap_exempt_signals"] = cfg.get("cap_exempt_signals", {}) or {}
    compiled["tiers"] = cfg.get("tiers", {}) or {}
    compiled["disclaimer"] = cfg.get("disclaimer", "")
    return compiled


def split_sentences(text: str) -> list[str]:
    """Rough sentence split. Job descriptions are bullet soup, so newlines and bullet glyphs end sentences too."""
    # "U.S." and "e.g." are not sentence ends; the patterns accept the bare "US" spelling.
    protected = re.sub(r"\bU\.S\.A\.", "USA", text or "")
    protected = re.sub(r"\bU\.S\.", "US", protected)
    protected = re.sub(r"\b(e\.g|i\.e|etc|vs|Inc|Corp|Ltd|St)\.", r"\1", protected)
    normalized = re.sub(r"[\r\n\u2022\u00b7\u25aa\u25cf\-]{2,}|[\r\n\u2022\u00b7\u25aa\u25cf]+", ". ", protected)
    # A line that already ended in punctuation must not gain a second full stop ("future..").
    normalized = re.sub(r"([.!?;])(?:\s*\.)+", r"\1", normalized)
    parts = re.split(r"(?<=[.!?;])\s+", normalized)
    return [p.strip() for p in parts if p.strip()]


def _first_match(patterns, sentence: str):
    for pattern in patterns:
        if pattern.search(sentence):
            return pattern
    return None


def _original_sentences(text: str) -> list[str]:
    """Split posting text without changing the wording returned as evidence."""
    # Mask only abbreviation punctuation, preserving every character's position.
    protected = re.sub(r"\b(?:U\.S\.(?:A\.)?|e\.g\.|i\.e\.|etc\.|vs\.|Inc\.|Corp\.|Ltd\.|St\.)",
                       lambda match: match.group().replace(".", "\x00"), text or "", flags=re.IGNORECASE)
    parts = re.split(r"(?<=[.!?;])\s+|[\r\n\u2022\u00b7\u25aa\u25cf]+", protected)
    return [part.replace("\x00", ".").strip() for part in parts if part.strip()]


# A note that reports the ABSENCE of restrictive wording ("No visa sponsorship or
# work-authorization sentence appears in the JD"; "The posting contains no statement about
# visa sponsorship, ... ITAR/EAR status"). When a posting page cannot be read, the gate reads
# the discovery AI's own description, whose restriction words appear only to say they are
# missing. Each guard needs a word about the text itself (sentence, wording, mention...) plus
# a verb of finding, so a real refusal ("No sponsorship is available") still excludes: no
# verb may sit between the "no" and that word. Both wordings above hid real entry-level
# postings (DMC, Western Governors University) before 2026-10-02.
_META = r"(?:sentences?|language|wording|mentions?|statements?|text|references?|clauses?|phrases?|indications?)"
_SEEN = r"(?:visible|found|present|shown|seen|stated|included|given|listed|located|identified|displayed|mentioned)"
_NO_VERB = r"(?:(?!\b(?:is|are|will|shall|can|be|been|being|offered|available|provided|sponsor|sponsors)\b)[^.;])"
ABSENCE_CLAIMS = [re.compile(pattern, re.IGNORECASE) for pattern in (
    rf"\b(?:no|none\s+of\s+the|not\s+any)\b{_NO_VERB}{{0,160}}\b{_META}\b[^.;]{{0,40}}\b(?:was|were|is|are|could\s+be)\s+(?:not\s+)?{_SEEN}\b",
    rf"\b(?:no|none\s+of\s+the|not\s+any)\b{_NO_VERB}{{0,160}}\b{_META}\b[^.;]{{0,40}}\b(?:appears?|exists?|occurs?)\b",
    rf"\b(?:did|do|does|could|can)\s*(?:not|n['’]t)\s+(?:see|find|show|locate|display|contain|include|mention|state|list|give)\b[^.;]{{0,120}}\b{_META}\b",
    rf"\b{_META}\b[^.;]{{0,120}}\b(?:was|were|is|are)\s+not\s+{_SEEN}\b",
    rf"\b(?:contains?|includes?|has|have|carries|carry|makes?|gives?)\s+(?:no|not\s+any)\s+{_META}\b",
    rf"\bthere\s+(?:is|are|was|were)\s+no\s+{_META}\b",
)]


INDEPENDENT_CLAUSE = re.compile(
    r"\b(?:but|however|although|though|except\s+that|and(?=\s+(?:"
    r"we\b|they\b|you\b|applicants\b|candidates\b|the\s+(?:company|employer|posting)\b|"
    r"this\s+(?:role|position)\b|cannot\b|can't\b|must\b|will\s+not\b|do(?:es)?\s+not\b)))\b",
    re.IGNORECASE,
)
_REQUIREMENT_NOUN = (r"(?:(?:a|an|any)\s+)?(?:(?:security|active|U\.?S\.?|United\s+States)\s+)?"
                     r"(?:clearance|citizenship|sponsorship|visa)")
NEGATED_REQUIREMENT_LIST = re.compile(
    r"\b(?:does|do|will)\s+not\s+require\s+" + _REQUIREMENT_NOUN
    + r"(?:\s*(?:,\s*(?:and|or)?|and|or)\s*" + _REQUIREMENT_NOUN + r")*",
    re.IGNORECASE,
)
NON_IMMIGRATION_SPONSOR = re.compile(
    r"\bsponsor(?:s|ing|ed)?\s+(?:(?:a|an|the|our)\s+)?(?:(?:local|community|charity|sports?|sporting|annual)\s+)?"
    r"(?:teams?|events?|conferences?|meetups?|hackathons?|projects?|content|research\s+grants?)\b",
    re.IGNORECASE,
)


# A clause that only PREFERS a clearance or citizenship does not bar Annie ("Active US
# Security clearance ... is beneficial, but not necessary": six Palantir software roles).
# Used for the cannot-hire group only, and only when the clause holds no requirement word.
PREFERRED_ONLY = re.compile(
    r"^(?=.*\b(?:a\s+plus|plus|preferred|beneficial|desired|desirable|nice[\s-]+to[\s-]+have|advantageous|bonus)\b)"
    r"(?!.*\b(?:required|requires?|must|mandatory|necessary\s+to|need\s+to|needs\s+to)\b).*$",
    re.IGNORECASE,
)


def _first_unguarded_match(patterns, sentence: str, guards):
    """The first pattern that matches outside every guarded phrase.

    Only the guarded wording is ignored, not the whole sentence: "No clearance needed,
    but we cannot sponsor visas" still excludes on its second clause.
    """
    protected = []
    for guard in guards:
        for match in guard.finditer(sentence):
            # "Could not see the precise sentence about security clearance" is a note about
            # missing text; the list that follows it belongs to that note too.
            end = len(sentence) if re.search(r"\b" + _META + r"\b", match.group(), re.IGNORECASE) else match.end()
            protected.append((match.start(), end))
    for pattern in patterns:
        for match in pattern.finditer(sentence):
            if not any(start < match.end() and match.start() < end for start, end in protected):
                return pattern
    return None


def screen(jd_text: str, rules: dict[str, Any] | None = None) -> Screen:
    """Read the posting's own words. Never raises on odd input.

    Per sentence: ignore guarded wording (negations such as "no clearance required",
    notes about absent wording, innocent "sponsor" nouns, the application form's
    sponsorship question), then Group 2 (cannot hire) and Group 1 (won't sponsor)
    exclude on the first unguarded hit. A contrast ("but", "however") starts a new
    clause, so a separate restriction in the same sentence still applies. Positive
    sentences are collected. A sentence matching only `do_not_exclude_on` ("must be
    authorized to work") can never exclude: Annie is authorized.
    """
    rules = rules or load_rules()
    everify = bool(_first_match(rules["everify_signals"], jd_text or ""))
    positives: list[dict] = []
    guards = [*rules["negation_guards"], *ABSENCE_CLAIMS, *rules["ambiguous_sponsor_noun"],
              NEGATED_REQUIREMENT_LIST, NON_IMMIGRATION_SPONSOR]
    for original in _original_sentences(jd_text or ""):
        for sentence in split_sentences(original):
            clauses = INDEPENDENT_CLAUSE.split(sentence)
            hard = next((match for clause in clauses
                         if (match := _first_unguarded_match(rules["exclude_cannot_hire"], clause, [*guards, PREFERRED_ONLY]))), None)
            soft = None if hard else next(
                (match for clause in clauses
                 if (match := _first_unguarded_match(rules["exclude_no_sponsorship"], clause, guards))), None)
            if hard or soft:
                # "Must be authorized to work in the US" on its own is fine; it only excludes
                # when a refusal phrase is present in the same sentence, which is what matched.
                matched = hard or soft
                return Screen(
                    verdict="EXCLUDED",
                    reason="cannot_hire" if hard else "no_sponsorship",
                    reason_label=("Requires citizenship / clearance / ITAR / permanent residency" if hard
                                  else "Posting explicitly will not sponsor"),
                    sentence=original[:400],
                    pattern=matched.pattern,
                    everify=everify,
                )
            positive = next((match for clause in clauses
                             if (match := _first_unguarded_match(rules["positive_sponsorship"], clause, guards))), None)
            if positive:
                positives.append({"pattern": positive.pattern, "sentence": original[:400]})
    if positives:
        return Screen("KEEP", "explicit_sponsorship", "Posting explicitly offers sponsorship",
                      sentence=positives[0]["sentence"], evidence=positives[:3], everify=everify)
    return Screen("KEEP", "silent", "Posting says nothing about sponsorship; the normal case", everify=everify)


# --------------------------------------------------------------------------
# Cap-exempt employers
# --------------------------------------------------------------------------
def normalize(name: str) -> str:
    text = (name or "").lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [t for t in text.split() if t]
    while tokens and tokens[-1] in SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def domain_of(url: str) -> str:
    try:
        return (urlsplit(url or "").hostname or "").lower()
    except ValueError:
        return ""


def is_cap_exempt(company: str, domain: str = "", rules: dict[str, Any] | None = None,
                  employer_type: str = "") -> tuple[bool, str]:
    """Universities, national labs, nonprofit research bodies and academic medical centers file year-round."""
    rules = rules or load_rules()
    signals = rules["cap_exempt_signals"]
    lowered = (company or "").lower()
    for suffix in signals.get("domains", [".edu", ".gov"]):
        if domain and domain.endswith(suffix):
            return True, f"domain {suffix}"
    for known in signals.get("known", []):
        if normalize(known) and normalize(known) in normalize(company):
            return True, f"known cap-exempt employer '{known}'"
    for needle in signals.get("name_contains", []):
        if needle.lower() in lowered:
            return True, f"name contains '{needle}'"
    if employer_type in {"university", "hospital", "national_lab", "nonprofit_research", "government"}:
        return True, f"employer type {employer_type}"
    return False, ""


# --------------------------------------------------------------------------
# H-1B history index
# --------------------------------------------------------------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS sponsors (
    employer_key TEXT NOT NULL, employer TEXT, approvals INTEGER DEFAULT 0, denials INTEGER DEFAULT 0,
    fiscal_year TEXT, state TEXT, city TEXT
);
CREATE INDEX IF NOT EXISTS ix_sponsors_key ON sponsors(employer_key);
CREATE TABLE IF NOT EXISTS sponsor_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1), csv_mtime REAL, csv_size INTEGER, rows INTEGER, built_at TEXT
);
"""


class SponsorIndex:
    """SQLite cache over the USCIS CSV; rebuilt whenever the CSV changes. Lookups take milliseconds."""

    def __init__(self, csv_path: Path = SPONSORS_CSV, db_path: Path = INDEX_DB):
        self.csv_path = Path(csv_path)
        self.db_path = Path(db_path)

    def _conn(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _csv_stat(self):
        if not self.csv_path.exists():
            return None
        stat = self.csv_path.stat()
        return (stat.st_mtime, stat.st_size)

    def is_current(self) -> bool:
        stat = self._csv_stat()
        if stat is None:
            return False
        try:
            with self._conn() as conn:
                conn.executescript(_SCHEMA)
                row = conn.execute("SELECT csv_mtime, csv_size FROM sponsor_meta WHERE id=1").fetchone()
        except sqlite3.Error:
            return False
        return bool(row) and row["csv_mtime"] == stat[0] and row["csv_size"] == stat[1]

    def build(self, force: bool = False) -> dict[str, Any]:
        stat = self._csv_stat()
        if stat is None:
            return {"built": False, "reason": "sponsors-uscis.csv is not present", "rows": 0}
        if not force and self.is_current():
            with self._conn() as conn:
                row = conn.execute("SELECT rows FROM sponsor_meta WHERE id=1").fetchone()
            return {"built": False, "reason": "already current", "rows": row["rows"] if row else 0}

        def to_int(value) -> int:
            try:
                return int(str(value or "0").strip() or 0)
            except ValueError:
                return 0

        rows = 0
        with self._conn() as conn:
            conn.executescript(_SCHEMA)
            conn.execute("DELETE FROM sponsors")
            with self.csv_path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
                batch: list[tuple] = []
                for record in csv.DictReader(handle):
                    batch.append((
                        (record.get("employer_key") or "").strip(), (record.get("employer") or "").strip(),
                        to_int(record.get("approvals")), to_int(record.get("denials")),
                        (record.get("fiscal_year") or "").strip(), (record.get("state") or "").strip(),
                        (record.get("city") or "").strip(),
                    ))
                    if len(batch) >= 5000:
                        conn.executemany("INSERT INTO sponsors VALUES (?,?,?,?,?,?,?)", batch)
                        rows += len(batch)
                        batch.clear()
                if batch:
                    conn.executemany("INSERT INTO sponsors VALUES (?,?,?,?,?,?,?)", batch)
                    rows += len(batch)
            conn.execute("INSERT OR REPLACE INTO sponsor_meta (id, csv_mtime, csv_size, rows, built_at) VALUES (1,?,?,?,datetime('now'))",
                         (stat[0], stat[1], rows))
        return {"built": True, "reason": "rebuilt from CSV", "rows": rows}

    def lookup(self, company: str, state: str = "") -> dict[str, Any]:
        key = normalize(company)
        empty = {"found": False, "matched_name": None, "approvals": 0, "denials": 0, "years": [], "states": [], "source": None}
        if not key or self._csv_stat() is None:
            return empty
        if not self.is_current():
            self.build()
        with self._conn() as conn:
            found = conn.execute("SELECT employer, approvals, denials, fiscal_year, state FROM sponsors WHERE employer_key=?", (key,)).fetchall()
        if not found:
            return empty
        years: list[str] = []
        states: list[str] = []
        approvals = denials = 0
        matched = None
        for row in found:
            approvals += row["approvals"] or 0
            denials += row["denials"] or 0
            matched = matched or row["employer"]
            for year in str(row["fiscal_year"] or "").replace(",", ";").split(";"):
                if year.strip() and year.strip() not in years:
                    years.append(year.strip())
            if row["state"] and row["state"] not in states:
                states.append(row["state"])
        if state and states and state.upper() not in [s.upper() for s in states]:
            pass  # name matched in another state: still counts as history, the caller sees the states list
        return {"found": True, "matched_name": matched, "approvals": approvals, "denials": denials,
                "years": sorted(years), "states": states, "source": "USCIS H-1B Employer Data Hub"}

    def stats(self) -> dict[str, Any]:
        if not self.is_current():
            self.build()
        with self._conn() as conn:
            row = conn.execute("SELECT rows, built_at FROM sponsor_meta WHERE id=1").fetchone()
        return {"employers": row["rows"] if row else 0, "built_at": row["built_at"] if row else None, "csv": str(self.csv_path)}


_INDEX: SponsorIndex | None = None


def index() -> SponsorIndex:
    global _INDEX
    if _INDEX is None:
        _INDEX = SponsorIndex()
    return _INDEX


# --------------------------------------------------------------------------
# Tier + the one call everyone makes
# --------------------------------------------------------------------------
def resolve_tier(result: Screen, cap_exempt: bool, approvals: int) -> str:
    if result.verdict == "EXCLUDED":
        return "EXCLUDED"
    if cap_exempt:
        return "S"
    if result.reason == "explicit_sponsorship":
        return "A"
    if approvals > 0:
        return "B"
    return "C"


def evaluate(company: str, jd_text: str, url: str = "", location: str = "",
             extra_sentences: list[str] | None = None, employer_type: str = "",
             rules: dict[str, Any] | None = None, sponsor_index: SponsorIndex | None = None) -> Verdict:
    """Gate a posting. `extra_sentences` lets discovery pass the verbatim restriction wording it found."""
    rules = rules or load_rules()
    text = jd_text or ""
    if extra_sentences:
        text = text + "\n" + "\n".join(s for s in extra_sentences if s)
    result = screen(text, rules)
    cap_exempt, cap_reason = is_cap_exempt(company, domain_of(url), rules, employer_type)
    sponsors = sponsor_index or index()
    history = sponsors.lookup(company, _state_of(location))
    if not history.get("found"):
        # A sponsor-board brand ("Robinhood") filed with USCIS under its legal name
        # (ROBINHOOD MARKETS INC): the registry built that link after checking the board.
        from backend.services.sponsor_boards import legal_key_for
        legal_key = legal_key_for(company)
        if legal_key:
            history = sponsors.lookup(legal_key, _state_of(location))
    tier = resolve_tier(result, cap_exempt, int(history.get("approvals") or 0))
    return Verdict(
        tier=tier, screen=result, cap_exempt=cap_exempt, cap_exempt_reason=cap_reason,
        h1b_found=bool(history.get("found")), h1b_matched_name=history.get("matched_name"),
        h1b_approvals=int(history.get("approvals") or 0), h1b_years=list(history.get("years") or []),
        h1b_denials=int(history.get("denials") or 0), everify=result.everify,
    )


_STATE = re.compile(r"\b([A-Z]{2})\b(?:\s+\d{5})?\s*$")


def _state_of(location: str) -> str:
    match = _STATE.search((location or "").strip().rstrip(",").strip())
    return match[1] if match else ""
