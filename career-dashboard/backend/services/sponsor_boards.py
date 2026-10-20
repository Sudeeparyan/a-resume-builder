"""H-1B sponsor boards: the public careers boards of employers in the USCIS H-1B data.

Annie's tracked companies (data/config/portals.yml) are a hand-picked list. The USCIS
H-1B Employer Data Hub (data/sponsors/sponsors-uscis.csv) names some 83,000 employers
that have actually sponsored H-1B workers. This module connects the two: it finds the
public job board of the larger sponsors on the applicant-tracking systems that publish
open JSON feeds (Greenhouse, Lever, Ashby, SmartRecruiters), so the no-AI "portals"
search pass can read every one of them, not only the companies someone remembered.

USCIS lists legal entities ("ROBINHOOD MARKETS INC"); boards are named after the brand
("robinhood"). For each employer a few slug guesses (at most ``MAX_VARIANTS``) are tried
on each system. A board is accepted only when both hold:

* it lists at least one current posting in the United States, and
* it is the same employer: the board's own name matches the legal name (exactly, as
  the brand of it, or at least ``SIMILARITY`` similar); for a board that states no name
  (Lever, Ashby), a US posting's own text must name the employer;
* when that match rests on one word left after dropping words from the legal name
  (MERCURY SYSTEMS INC is "mercury", the name of an unrelated fintech's board too), a US
  posting must also be in the city or state where USCIS records the employer.

Everything else stays out, with what was tried and why. The result is
data/sponsors/sponsor-boards.csv, built by backend/scripts/build_sponsor_boards.py.
Sponsorship history stays a ranking signal: a company with no board, or no H-1B record,
is still searched by the AI pass and still shown when its posting is silent.

At search time ``due_rows`` hands the portals pass the boards read least recently
(``READ_PER_PASS`` per pass, so a morning run stays inside its time budget), and
``record_reads`` remembers each read. A board that has gone (HTTP 404) is set aside
for ``GONE_DAYS`` and then tried again; the next build drops it for good.
"""
from __future__ import annotations

import csv
import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

from backend.services.sponsorship import SPONSORS_DIR, normalize

BOARDS_CSV = SPONSORS_DIR / "sponsor-boards.csv"
FIELDS = ["employer", "legal_name", "employer_key", "ats", "token", "h1b_approvals", "h1b_denials",
          "fiscal_years", "us_postings", "target_postings", "name_check", "verified_on"]
KINDS = ("greenhouse", "lever", "ashby", "smartrecruiters")
ATS_LABELS = {"greenhouse": "Greenhouse", "lever": "Lever", "ashby": "Ashby", "smartrecruiters": "SmartRecruiters"}
CAREERS_URL = {"greenhouse": "https://job-boards.greenhouse.io/{token}", "lever": "https://jobs.lever.co/{token}",
               "ashby": "https://jobs.ashbyhq.com/{token}", "smartrecruiters": "https://jobs.smartrecruiters.com/{token}"}
SIMILARITY = 0.85
MAX_VARIANTS = 3
READ_PER_PASS = 120
GONE_DAYS = 30

# Trailing words a brand's board name leaves out ("Robinhood" for ROBINHOOD MARKETS INC).
# sponsorship.normalize already drops legal forms (inc, llc, corp, technologies, labs ...).
DESCRIPTORS = {"com", "markets", "platforms", "platform", "software", "networks", "network", "health", "energy",
               "financial", "partners", "digital", "data", "global", "consulting", "operations", "ventures",
               "enterprises", "industries", "brands", "media", "interactive", "capital", "the"}
# First words too common to be a brand on their own ("american", "national" ...).
STOP_BRANDS = {"american", "national", "united", "first", "general", "global", "new", "the", "north", "south",
               "east", "west", "advanced", "applied", "digital", "data", "tech", "info", "bank", "city", "state",
               "pacific", "atlantic", "central", "premier", "integrated", "innovative", "smart", "next", "blue",
               "green", "red", "one", "my", "open", "big", "great", "best", "true", "pro", "star", "sun", "us"}
# Employers whose jobs are on public-sector, hospital or school sites, not on these boards.
NOT_ATS = re.compile(r"(?i)\b(university|college|school|hospital|medical center|health system|clinic|county|"
                     r"city of|state of|department of|board of|district|academy|church|physicians?)\b")
# Words a board's title adds around the employer's name ("Careers at Plaid", "Acme Jobs").
_BOARD_WORDS = re.compile(r"(?i)\b(careers?|jobs?|job board|openings|join us|hiring|work at)\b")
_LEADING_AT = re.compile(r"(?i)^\s*(at|with)\s+")


# ---- the registry file ----------------------------------------------------------------

def load(path: Path | None = None) -> list[dict[str, str]]:
    """The registry's rows; empty when the file is absent. A malformed file is an error."""
    path = Path(path or BOARDS_CSV)
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"{path.name} has unexpected columns; rebuild it with build_sponsor_boards.py")
        return [dict(row) for row in reader]


def write(rows: list[dict[str, Any]], path: Path | None = None) -> None:
    path = Path(path or BOARDS_CSV)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})
    temp.replace(path)


def _stamp(path: Path) -> tuple[float, int]:
    try:
        stat = path.stat()
        return stat.st_mtime, stat.st_size
    except OSError:
        return 0.0, 0


@lru_cache(maxsize=4)
def _legal_keys(path: str, _stamp: tuple[float, int]) -> dict[str, str]:
    try:
        rows = load(Path(path))
    except (OSError, ValueError, csv.Error):
        return {}
    return {normalize(row["employer"]): row["employer_key"] for row in rows if row.get("employer_key")}


def legal_key_for(company: str, path: Path | None = None) -> str:
    """The USCIS employer key a registry board's brand name stands for ("" when none).

    The registry shows "Robinhood"; USCIS files it as ROBINHOOD MARKETS INC. The sponsorship
    gate uses this to find the H-1B record behind a brand name."""
    path = Path(path or BOARDS_CSV)
    return _legal_keys(str(path), _stamp(path)).get(normalize(company), "")


# ---- candidates from the USCIS data -------------------------------------------------------

def candidates(top: int, *, min_approvals: int = 5, skip: set[str] | None = None,
               csv_path: Path | None = None) -> list[dict[str, Any]]:
    """The ``top`` H-1B employers by approvals that might publish a public board."""
    from backend.services.sponsorship import SPONSORS_CSV

    skip = skip or set()
    out = []
    with Path(csv_path or SPONSORS_CSV).open(encoding="utf-8", errors="replace", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                approvals = int(row.get("approvals") or 0)
                denials = int(row.get("denials") or 0)
            except ValueError:
                continue
            key = (row.get("employer_key") or "").strip()
            name = (row.get("employer") or "").strip()
            if approvals < min_approvals or not key or key in skip or NOT_ATS.search(name):
                continue
            out.append({"employer_key": key, "legal_name": name, "h1b_approvals": approvals,
                        "h1b_denials": denials, "fiscal_years": (row.get("fiscal_year") or "").strip(),
                        "state": (row.get("state") or "").strip(), "city": (row.get("city") or "").strip()})
    out.sort(key=lambda c: (-c["h1b_approvals"], c["employer_key"]))
    return out[:top]


# ---- names ------------------------------------------------------------------------------

def _tokens(name: str) -> list[str]:
    return normalize(name).split()


def _core(tokens: list[str]) -> list[str]:
    core = list(tokens)
    while len(core) > 1 and core[-1] in DESCRIPTORS:
        core.pop()
    while len(core) > 1 and core[0] == "the":
        core.pop(0)
    return core


def slug_variants(legal_name: str) -> list[str]:
    """At most three board names to try: the brand, the full name, then the first word."""
    tokens = _tokens(legal_name)
    if not tokens or (len(tokens) == 1 and (tokens[0] in STOP_BRANDS or len(tokens[0]) < 3)):
        return []
    core = _core(tokens)
    if len(core) == 1 and (core[0] in STOP_BRANDS or len(core[0]) < 4) and len(tokens) > 1:
        core = tokens  # "global data services" is not the board "global"
    out = ["".join(core), "-".join(core) if len(core) > 1 else "", "".join(tokens) if tokens != core else ""]
    first = core[0]
    if len(core) > 1 and len(first) >= 5 and first not in STOP_BRANDS:
        out.append(first)
    return [slug for slug in dict.fromkeys(s for s in out if len(s) >= 3)][:MAX_VARIANTS]


def display_name(legal_name: str) -> str:
    """A readable brand from a USCIS legal name: "ROBINHOOD MARKETS INC" -> "Robinhood Markets"."""
    words = normalize(legal_name).split() or legal_name.split()
    return " ".join(word.capitalize() for word in words)


def name_match(board_name: str, legal_name: str) -> str:
    """How a board's own name names this employer: "exact", "similar", "brand", or ""."""
    board = " ".join(normalize(_LEADING_AT.sub("", _BOARD_WORDS.sub(" ", board_name or ""))).split())
    legal = " ".join(_tokens(legal_name))
    if not board or not legal:
        return ""
    if board == legal or board.replace(" ", "") == legal.replace(" ", ""):
        return "exact"
    if SequenceMatcher(None, board.replace(" ", ""), legal.replace(" ", "")).ratio() >= SIMILARITY:
        return "similar"
    board_tokens, legal_tokens = board.split(), legal.split()
    if (legal_tokens[:len(board_tokens)] == board_tokens and len(board.replace(" ", "")) >= 4
            and board_tokens[0] not in STOP_BRANDS and all(t in DESCRIPTORS for t in legal_tokens[len(board_tokens):])):
        return "brand"  # ROBINHOOD MARKETS INC is the board "Robinhood"
    return ""


def named_in_text(texts: list[str], legal_name: str) -> bool:
    """Whether a posting's own text names the employer by a distinctive brand."""
    core = _core(_tokens(legal_name))
    phrase = " ".join(core)
    if not phrase or (len(core) == 1 and (len(phrase) < 5 or phrase in STOP_BRANDS)):
        return False
    pattern = re.compile(r"(?<![a-z0-9])" + r"[\s\-]*".join(re.escape(token) for token in core) + r"(?![a-z0-9])")
    return any(pattern.search((text or "").casefold()) for text in texts)


# ---- one probe: a board's postings and its own employer name -----------------------------

def _us(location: str, country: str = "") -> bool:
    from backend.job_quality import is_us_location

    country = (country or "").strip().casefold()
    return country in {"us", "usa", "united states", "united states of america"} or is_us_location(location or "")


def _missing(error: str | None) -> bool:
    return bool(error) and error.startswith("HTTP 404")


def probe(kind: str, slug: str, get_json: Callable | None = None) -> dict[str, Any] | None:
    """{"ats","token","name","postings":[{"title","location","us","text"}],"error"}; None when no board."""
    if get_json is None:
        from backend.services.portals import _get_json as get_json
    from backend.services.portals import html_to_text

    board: dict[str, Any] = {"ats": kind, "token": slug, "name": "", "postings": [], "error": None}
    if kind == "greenhouse":
        data, error = get_json(f"https://boards-api.greenhouse.io/v1/boards/{quote(slug)}/jobs")
        if not isinstance(data, dict):
            return None if _missing(error) or error is None else {**board, "error": error}
        for job in data.get("jobs") or []:
            if isinstance(job, dict):
                where = str((job.get("location") or {}).get("name") or "")
                board["postings"].append({"title": str(job.get("title") or ""), "location": where, "us": _us(where), "text": ""})
        if board["postings"]:
            about, _ = get_json(f"https://boards-api.greenhouse.io/v1/boards/{quote(slug)}")
            board["name"] = " ".join(str((about or {}).get("name") or "").split()) if isinstance(about, dict) else ""
        return board
    if kind == "lever":
        data, error = get_json(f"https://api.lever.co/v0/postings/{quote(slug)}?mode=json")
        if not isinstance(data, list):
            return None if _missing(error) or error is None else {**board, "error": error}
        for job in data:
            if isinstance(job, dict):
                cats = job.get("categories") or {}
                where = "; ".join(dict.fromkeys([str(cats.get("location") or "")] + [str(p) for p in cats.get("allLocations") or []]))
                text = str(job.get("descriptionPlain") or "") + "\n" + str(job.get("additionalPlain") or "")
                board["postings"].append({"title": str(job.get("text") or ""), "location": where,
                                          "us": _us(where, str(job.get("country") or "")), "text": text})
        return board
    if kind == "ashby":
        data, error = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{quote(slug)}")
        if not isinstance(data, dict):
            return None if _missing(error) or error is None else {**board, "error": error}
        for job in data.get("jobs") or []:
            if isinstance(job, dict):
                where = "; ".join(dict.fromkeys([str(job.get("location") or "")] + [
                    str(s.get("location") or "") for s in job.get("secondaryLocations") or [] if isinstance(s, dict)]))
                country = str((((job.get("address") or {}).get("postalAddress")) or {}).get("addressCountry") or "")
                board["postings"].append({"title": str(job.get("title") or ""), "location": where,
                                          "us": _us(where, country),
                                          "text": str(job.get("descriptionPlain") or html_to_text(job.get("descriptionHtml") or ""))})
        return board
    if kind == "smartrecruiters":
        data, error = get_json(f"https://api.smartrecruiters.com/v1/companies/{quote(slug)}/postings?country=us&limit=100")
        if not isinstance(data, dict):
            return None if _missing(error) or error is None else {**board, "error": error}
        content = [job for job in data.get("content") or [] if isinstance(job, dict)]
        if not content:
            return None  # SmartRecruiters answers 200 with an empty list for a name it does not know
        names = [str((job.get("company") or {}).get("name") or "") for job in content]
        board["name"] = max(set(names), key=names.count)
        for job in content:
            place = job.get("location") or {}
            where = ", ".join(str(place.get(k) or "") for k in ("city", "region", "country") if place.get(k))
            board["postings"].append({"title": str(job.get("name") or ""), "location": where,
                                      "us": _us(where, str(place.get("country") or "")), "text": ""})
        return board
    raise ValueError(f"Unknown applicant-tracking system {kind!r}")


# Legal forms only: dropping these never makes a name ambiguous (ROBLOX CORPORATION is Roblox).
LEGAL_FORMS = {"inc", "incorporated", "llc", "l", "c", "ltd", "limited", "corp", "corporation", "company", "co", "plc",
               "lp", "llp", "pllc", "pc", "the", "and"}
_STATE_NAMES = ("alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|georgia|hawaii|idaho|"
                "illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|"
                "mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|new york|"
                "north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|south carolina|"
                "south dakota|tennessee|texas|utah|vermont|virginia|washington|west virginia|wisconsin|wyoming|"
                "district of columbia").split("|")
_STATE_ABBR = ("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH "
               "OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC").split()
STATE_NAME = dict(zip(_STATE_ABBR, _STATE_NAMES))


def needs_place_check(legal_name: str) -> bool:
    """True when the brand is one word left after dropping descriptive words from the legal name."""
    plain = [t for t in re.sub(r"[^a-z0-9]+", " ", (legal_name or "").casefold().replace("&", " and ")).split()
             if t not in LEGAL_FORMS]
    return len(_core(_tokens(legal_name))) == 1 and len(plain) > 1


def in_place(location: str, state: str, city: str) -> bool:
    """Whether a posting's location names the USCIS city or state."""
    text = f" {(location or '').casefold()} "
    state = (state or "").upper()
    if city and f" {city.casefold()}" in text.replace(",", " "):
        return True
    if state in STATE_NAME and (re.search(r"(?:,|\s)" + state + r"\b", location or "")  # upper case only: "or" is not Oregon
                                or STATE_NAME[state] in text):
        return True
    return False


def judge(board: dict[str, Any], legal_name: str, state: str = "", city: str = "") -> dict[str, Any]:
    """Accept or refuse one board for this employer, with the reason either way."""
    from backend.services.portals import title_worth_opening

    us = [p for p in board["postings"] if p["us"]]
    target = [p for p in us if title_worth_opening(p["title"])]
    result = {"ats": board["ats"], "token": board["token"], "board_name": board["name"],
              "postings": len(board["postings"]), "us_postings": len(us), "target_postings": len(target),
              "accepted": False, "reason": ""}
    if board.get("error"):
        return {**result, "reason": f"not read: {board['error']}"}
    if not us:
        return {**result, "reason": "no current posting in the United States"}
    if board["name"]:
        match = name_match(board["name"], legal_name)
        if not match:
            return {**result, "reason": f"board name {board['name']!r} is another employer"}
        accepted = {**result, "accepted": True, "match": match, "reason": f"board name: {board['name']} ({match})"}
    elif named_in_text([p["text"] or p["title"] for p in us], legal_name):
        accepted = {**result, "accepted": True, "match": "text", "reason": "a US posting's own text names the employer"}
    else:
        return {**result, "reason": "the board states no employer name and no US posting names this employer"}
    if needs_place_check(legal_name) and (state or city):
        if not any(in_place(p["location"], state, city) for p in us):
            place = ", ".join(part for part in (city.title(), state) if part)
            return {**result, "reason": f"{accepted['reason']}, but the name is one common word and no US posting "
                                        f"is in {place}, where USCIS records this employer"}
        accepted["reason"] += f"; a US posting is in {', '.join(part for part in (city.title(), state) if part)}"
    return accepted


def resolve(legal_name: str, get_json: Callable | None = None, kinds: tuple[str, ...] = KINDS,
            state: str = "", city: str = "") -> dict[str, Any]:
    """The first accepted board for one USCIS employer, or what was tried and refused."""
    tried, refused = [], []
    for slug in slug_variants(legal_name):
        for kind in kinds:
            tried.append(f"{kind}:{slug}")
            board = probe(kind, slug, get_json)
            if board is None:
                continue
            verdict = judge(board, legal_name, state, city)
            if verdict["accepted"]:
                return {"status": "resolved", "legal_name": legal_name, **verdict, "tried": tried}
            refused.append(verdict)
    return {"status": "unresolved", "legal_name": legal_name, "tried": tried, "refused": refused}


def registry_row(found: dict[str, Any], candidate: dict[str, Any], on: str) -> dict[str, Any]:
    by_board_name = found.get("match") in {"exact", "similar", "brand"} and found.get("board_name")
    return {"employer": " ".join(str(found["board_name"]).split()) if by_board_name else display_name(candidate["legal_name"]),
            "legal_name": candidate["legal_name"], "employer_key": candidate["employer_key"],
            "ats": found["ats"], "token": found["token"], "h1b_approvals": candidate["h1b_approvals"],
            "h1b_denials": candidate["h1b_denials"], "fiscal_years": candidate["fiscal_years"],
            "us_postings": found["us_postings"], "target_postings": found["target_postings"],
            "name_check": found["reason"], "verified_on": on}


# ---- at search time ------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def board_id(row: dict[str, Any]) -> str:
    return f"{row.get('ats')}:{row.get('token') or row.get('ats_token')}"


def portal_row(row: dict[str, str]) -> dict[str, Any]:
    """A registry row in the shape portals.fetch_board reads, with why it is trusted."""
    label = ATS_LABELS.get(row["ats"], row["ats"])
    approvals = int(row.get("h1b_approvals") or 0)
    years = (row.get("fiscal_years") or "").replace(";", ", ")
    return {"name": row["employer"], "ats": row["ats"], "ats_token": row["token"],
            "careers_url": CAREERS_URL.get(row["ats"], "").format(token=row["token"]),
            "legal_name": row["legal_name"], "employer_key": row["employer_key"], "_source": "sponsor_board",
            "_vouched": (f"{row['legal_name']} is in the USCIS H-1B employer data ({approvals:,} approvals"
                         + (f", FY {years}" if years else "") + "), and this posting was read from the employer's own "
                         f"careers board ({label}), which the sponsor-board registry matched to that employer "
                         f"({row.get('name_check') or 'checked'}).")}


def due_rows(db, limit: int = READ_PER_PASS, skip_names: set[str] | None = None,
             path: Path | None = None) -> list[dict[str, Any]]:
    """The registry boards to read this pass: never read first, then least recently read."""
    try:
        rows = load(path)
    except (OSError, ValueError, csv.Error):
        return []
    skip = {normalize(name) for name in skip_names or set()}
    reads = {r[0]: (r[1], r[2]) for r in db.execute("SELECT board, last_read, gone_until FROM sponsor_board_reads")}
    now = _now().isoformat()
    due = []
    for row in rows:
        if normalize(row["employer"]) in skip or row["employer_key"] in skip:
            continue  # Annie already tracks this employer in portals.yml
        last, gone = reads.get(board_id(row), ("", None))
        if gone and gone > now:
            continue
        due.append((last or "", -int(row.get("h1b_approvals") or 0), row))
    due.sort(key=lambda item: item[:2])
    return [portal_row(row) for _last, _approvals, row in due[:max(0, limit)]]


def record_reads(db, results: list[tuple[dict[str, Any], int, str | None]]) -> None:
    """Remember each board read (row, postings found, error); a gone board rests GONE_DAYS."""
    now = _now()
    for row, count, error in results:
        gone = (now + timedelta(days=GONE_DAYS)).isoformat() if _missing(error) else None
        db.execute(
            "INSERT INTO sponsor_board_reads(board,last_read,postings,error,gone_until) VALUES(?,?,?,?,?) "
            "ON CONFLICT(board) DO UPDATE SET last_read=excluded.last_read, postings=excluded.postings, "
            "error=excluded.error, gone_until=excluded.gone_until",
            (board_id(row), now.isoformat(), int(count), error or "", gone),
        )


def stats(db=None, path: Path | None = None) -> dict[str, Any]:
    """How many boards the registry holds and how many a search has read."""
    try:
        rows = load(path)
    except (OSError, ValueError, csv.Error) as exc:
        return {"boards": 0, "error": str(exc)}
    by_ats: dict[str, int] = {}
    for row in rows:
        by_ats[row["ats"]] = by_ats.get(row["ats"], 0) + 1
    out: dict[str, Any] = {"boards": len(rows), "by_ats": by_ats,
                           "verified_on": max((row["verified_on"] for row in rows), default="")}
    if db is not None:
        read = db.execute("SELECT COUNT(*), MAX(last_read) FROM sponsor_board_reads").fetchone()
        out.update(read_ever=read[0], last_read=read[1] or "")
    return out
