"""Deterministic posting freshness, hard relevance gates, legitimacy and batch selection.

The fit score itself comes from the job's verified requirement matrix (services/fit.py)."""

from __future__ import annotations

import hashlib
import json
import re
import socket
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


ATS_DOMAINS = {
    "ashbyhq.com",
    "bamboohr.com",
    "greenhouse.io",
    "jobs.lever.co",
    "myworkdayjobs.com",
    "recruitee.com",
    "smartrecruiters.com",
    "teamtailor.com",
    "workable.com",
}
# US states, abbreviations, big hubs and "remote (US)". Anything else is not pursued.
_STATES = (
    "alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|georgia|hawaii|idaho|illinois|"
    "indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi|missouri|"
    "montana|nebraska|nevada|new hampshire|new jersey|new mexico|new york|north carolina|north dakota|ohio|oklahoma|"
    "oregon|pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|utah|vermont|virginia|washington|"
    "west virginia|wisconsin|wyoming|district of columbia"
)
_ABBR = "AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC"
_HUBS = r"new york city|nyc|san francisco|bay area|silicon valley|seattle|austin|boston|chicago|raleigh|durham|minneapolis|los angeles|san diego|san jose|denver|atlanta|dallas|houston|phoenix|portland|pittsburgh|philadelphia|washington,? d\.?c\.?"
# How a feed may end a location after the state: "Alameda, CA — on-site", "Austin, TX (Hybrid)". Only
# work-arrangement words, so a trailing country ("Munich, DE, Germany") still decides for itself.
_ARRANGEMENT = (r"(?:\s*[-–—|/;:(,]?\s*(?:on[- ]?site|in[- ]office|in[- ]person|hybrid|remote|"
                r"full[- ]time|part[- ]time)\s*\)?)*")
US_LOCATION = re.compile(
    r"(?i)\b(?:united states|u\.?s\.?a?\.?|usa|us[- ]remote|remote[- ,(]*(?:us|usa|united states)|" + _STATES + "|" + _HUBS + r")\b"
    r"|,\s*(?:" + _ABBR + r")\b(?:\s+\d{5})?\s*(?:,\s*(?:usa?|united states))?" + _ARRANGEMENT + r"\s*$"
    r"|\b(?:" + _ABBR + r")\s+\d{5}\b"
)
# Countries, regions and cities with no US namesake: only a strong US marker outweighs them.
# The cities matter where a feed writes the country as a code that is also a US state
# ("Mumbai, IN", "Munich, DE", "Tel Aviv, IL", "Montreal, CA", "Bogota, CO", "Jakarta, ID").
_FOREIGN_PLACES = (
    r"ireland|united kingdom|uk|england|scotland|wales|canada|toronto|montreal|montréal|ottawa|calgary|edmonton|"
    r"mississauga|markham|kitchener|winnipeg|quebec|québec|british columbia|alberta|"
    r"india|bangalore|bengaluru|hyderabad|chennai|pune|mumbai|bombay|new delhi|noida|gurgaon|gurugram|kolkata|"
    r"ahmedabad|coimbatore|kochi|cochin|trivandrum|thiruvananthapuram|jaipur|indore|chandigarh|mysore|mysuru|nagpur|"
    r"germany|munich|münchen|frankfurt|düsseldorf|dusseldorf|"
    r"israel|tel aviv|herzliya|haifa|jerusalem|petah tikva|ra'?anana|netanya|yokneam|"
    r"france|netherlands|rotterdam|eindhoven|spain|barcelona|portugal|lisbon|italy|switzerland|zurich|"
    r"zürich|austria|belgium|brussels|sweden|stockholm|norway|oslo|denmark|copenhagen|finland|helsinki|"
    r"poland|warszawa|krakow|kraków|wroclaw|wrocław|czech|prague|romania|bucharest|cluj|hungary|budapest|ukraine|kyiv|"
    r"kiev|lviv|estonia|tallinn|lithuania|vilnius|latvia|riga|greece|turkey|istanbul|serbia|belgrade|croatia|bulgaria|"
    r"sofia|tbilisi|batumi|armenia|yerevan|"
    r"singapore|australia|sydney|melbourne|brisbane|new zealand|auckland|japan|tokyo|osaka|china|beijing|shanghai|"
    r"shenzhen|hangzhou|hong kong|taiwan|taipei|korea|seoul|vietnam|hanoi|ho chi minh|philippines|manila|cebu|"
    r"malaysia|kuala lumpur|thailand|bangkok|indonesia|jakarta|pakistan|karachi|lahore|islamabad|bangladesh|dhaka|"
    r"sri lanka|nepal|kathmandu|uae|dubai|abu dhabi|saudi|riyadh|qatar|doha|egypt|cairo|nigeria|lagos|kenya|nairobi|"
    r"south africa|cape town|johannesburg|"
    r"mexico|guadalajara|monterrey|brazil|são paulo|sao paulo|rio de janeiro|argentina|buenos aires|colombia|bogota|"
    r"bogotá|medellin|medellín|chile|santiago|uruguay|montevideo|costa rica|"
    r"emea|apac|latam|europe|asia"
)
_FOREIGN_STRONG = re.compile(r"(?i)\b(?:" + _FOREIGN_PLACES + r")\b")
# Cities that also exist in the US (Dublin OH/CA, London KY, Vancouver WA, Paris TX, Berlin NH, Amsterdam NY).
_FOREIGN_TWIN = re.compile(r"(?i)\b(?:dublin|london|vancouver|paris|berlin|amsterdam|ontario|geneva|milan|madrid|delhi|"
                           r"hamburg|stuttgart|cologne|peru|warsaw|athens|rome|lima)\b")
_US_STRONG = re.compile(
    r"(?i)\b(?:united states|u\.s\.a?\.?|usa|us[- ]remote|remote[- ,(]*(?:us|usa|united states)|" + _STATES + r")\b|\b\d{5}(?:-\d{4})?\b"
)
# A trailing two-letter US state. DE and IN are left out: in job feeds they almost always mean Germany and India.
_US_STATE_SUFFIX = re.compile(r",\s*(?:" + "|".join(a for a in _ABBR.split("|") if a not in {"DE", "IN"}) + r")\b")
# So a trailing IN or DE with no other US marker counts only after a known Indiana or
# Delaware city: "Vellore, IN" and "Leipzig, DE" are not American.
_IN_DE_SUFFIX = re.compile(r"(?i),\s*(?:IN|DE)\s*(?:\d{5})?\s*$")
_IN_DE_CITIES = re.compile(
    r"(?i)\b(?:indianapolis|fort wayne|evansville|south bend|carmel|fishers|bloomington|west lafayette|lafayette|"
    r"hammond|gary|muncie|terre haute|noblesville|kokomo|columbus|elkhart|mishawaka|anderson|greenwood|westfield|"
    r"zionsville|plainfield|warsaw|jeffersonville|new albany|valparaiso|merrillville|richmond|goshen|crown point|avon|"
    r"brownsburg|franklin|batesville|jasper|seymour|notre dame|whitestown|lebanon|greenfield|michigan city|portage|"
    r"wilmington|dover|newark|middletown|lewes|georgetown|milford|smyrna|new castle|hockessin|seaford)\b"
)
# One posting can list several places ("San Francisco, CA; Toronto, ON" or "Austin, TX or Remote, Canada").
_PLACE_SEPARATOR = re.compile(r"\s*(?:;|\||\s/\s)\s*|\s+or\s+")


def _is_us_place(location: str) -> bool:
    if not US_LOCATION.search(location):
        return False
    us_words = {match.group().casefold() for match in _US_STRONG.finditer(location)}
    # "Tbilisi, Georgia": the only US word is the state that shares the country's name.
    if us_words and not (us_words == {"georgia"} and _FOREIGN_STRONG.search(location)):
        return True
    if _FOREIGN_STRONG.search(location):
        return False
    if _IN_DE_SUFFIX.search(location):
        return bool(_IN_DE_CITIES.search(location))
    return not _FOREIGN_TWIN.search(location) or bool(_US_STATE_SUFFIX.search(location))


# A posting listed only as "Remote" whose text places the work abroad ("remote within Canada",
# "candidates based in the UK") and never in the US.
_WHERE_VERB = r"(?:based|located|living|resid(?:e|es|ing|ent|ents)|remote(?:ly)?|work(?:ing)?|hire|hiring|candidates|anywhere)"
_REMOTE_ABROAD = re.compile(
    r"(?i)\b" + _WHERE_VERB + r"\s+(?:only\s+)?(?:in|from|within|across)\s+(?:the\s+)?(?:" + _FOREIGN_PLACES + r")\b"
)
_REMOTE_US = re.compile(
    r"(?i)\b" + _WHERE_VERB + r"\s+(?:only\s+)?(?:in|from|within|across)\s+(?:the\s+)?(?:continental\s+)?"
    r"(?:united states|u\.s\.a?\.?|us|usa)\b|\bus[- ]based\b|\bremote[- ,(]*(?:us|usa|united states)\b"
)


def remote_outside_us(description: str) -> bool:
    """True when a bare-"Remote" posting's own text puts the work outside the US only."""
    text = description or ""
    return bool(_REMOTE_ABROAD.search(text)) and not _REMOTE_US.search(text)


def is_us_location(location: str) -> bool:
    """True for a US city, state, hub or US-remote location.

    Dublin, OH and Vancouver, WA are American; Dublin, Ireland, Vancouver, BC and
    Bengaluru, IN are not. A posting that offers the US among other places counts.
    """
    places = [part for part in _PLACE_SEPARATOR.split(location or "") if part.strip()]
    return any(_is_us_place(place) for place in places)
SENIORITY_BLOCK = re.compile(r"\b(senior|sr\.?|staff|lead|principal|director|dir|head(?: of)?|manager|architect|distinguished|fellow|vp|vice president)\b", re.I)
# Internships, co-ops and apprenticeships are for students; Annie completed her MS in May
# 2026 and wants a full-time role (profile.yml target_roles.seniority has no intern level).
INTERNSHIP = re.compile(r"\b(intern|interns|internship|co-?op|apprentice(?:ship)?)\b", re.I)
# Annie holds a Master's. A PhD that is merely preferred, or one option among degrees ("MS or PhD"),
# is fine; a posting that requires one is not hers.
_PHD = r"ph\.?\s?d\.?"
_PHD_TITLE = re.compile(r"\b" + _PHD + r"\b", re.I)
_PHD_REQUIRED = re.compile(
    r"\b" + _PHD + r"\b[^.\n]{0,30}\b(is\s+)?required\b|\bmust\s+(have|hold)\s+(a\s+)?" + _PHD + r"\b"
    r"|\b(currently\s+)?(pursuing|enrolled\s+in)\s+(a\s+)?" + _PHD + r"\b|\b" + _PHD + r"\s+(candidates?|students?)\s+only\b",
    re.I,
)
_PHD_ONLY_BULLET = re.compile(r"^\s*(?:[-*•·]\s*)?(?:a\s+|an?\s+)?" + _PHD + r"\b(?:\s+degree)?\s+(?:in|from)\b", re.I | re.M)
_OTHER_DEGREE = re.compile(r"\b(m\.?s\.?c?|master'?s?|b\.?s\.?c?|bachelor'?s?|b\.?e\.?|m\.?eng|equivalent)\b", re.I)


def requires_phd(title: str, description: str) -> bool:
    """True when the posting is only for PhD holders or PhD students."""
    if _PHD_TITLE.search(title or ""):
        return True
    text = description or ""
    if _PHD_REQUIRED.search(text):
        return True
    for match in _PHD_ONLY_BULLET.finditer(text):
        line = text[match.start(): text.find("\n", match.start()) if text.find("\n", match.start()) != -1 else len(text)]
        if not _OTHER_DEGREE.search(line) and not re.search(r"\b(preferred|plus|nice to have|bonus)\b", line, re.I):
            return True
    return False
# Annie completed her MS in May 2026 and is on OPT, so a role reserved for current students
# is not hers ("Must be actively enrolled in an accredited college/university program during
# the time of the internship", three Snowflake internships prepared in September 2026).
# A posting that also takes recent graduates is fine.
_ENROLLMENT_REQUIRED = re.compile(
    r"\b(?:currently|actively)\s+(?:enrolled|pursuing|working\s+toward)\b"
    r"|\breturning\s+to\s+(?:school|university|college|your\s+(?:studies|degree|program))\b"
    r"|\bmust\s+be\s+(?:a\s+)?(?:current(?:ly)?\s+)?(?:enrolled\s+)?(?:full[- ]time\s+)?student\b"
    r"|\b(?:at\s+least\s+one|one\s+or\s+more)\s+(?:semester|quarter|term)s?\s+(?:remaining|left)\b",
    re.I,
)
_GRADUATES_WELCOME = re.compile(
    r"\bor\s+(?:have\s+)?(?:recently\s+)?(?:completed|graduated|earned|obtained|hold)\b|\brecent(?:ly)?\s+graduat",
    re.I,
)


def requires_enrollment(description: str) -> bool:
    """True when the posting is only for current students (a PhD-only posting is checked separately)."""
    text = description or ""
    for match in _ENROLLMENT_REQUIRED.finditer(text):
        if re.match(r"(?i)(?:currently|actively)\s+pursuing\s+(?:a\s+)?ph\.?\s?d", match.group() + text[match.end():match.end() + 12]):
            continue  # requires_phd() reports that one
        window = text[max(0, match.start() - 120): match.end() + 160]
        if not _GRADUATES_WELCOME.search(window):
            return True
    return False


_YEARS = re.compile(r"(\d{1,2})\s*\+?\s*(?:-|to|–)?\s*(?:\d{1,2})?\s*\+?\s*(?:years?|yrs)\b(?:\s+of)?\s+(?:\w+\s+){0,4}?(?:experience|exp)", re.I)


def years_required(description: str) -> int | None:
    """Smallest years figure a JD asks for, or None. Sentences about the company's age are ignored."""
    found = []
    for match in _YEARS.finditer(description or ""):
        window = (description or "")[max(0, match.start() - 25): match.start()].casefold()
        after = (description or "")[match.end(): match.end() + 12].casefold()
        if re.search(r"\b(founded|since|over the (last|past)|for the (last|past))\b", window) or after.lstrip().startswith("ago"):
            continue
        found.append(int(match[1]))
    return min(found) if found else None


def _load_profile(root=None) -> dict:
    try:
        import yaml
        from backend.paths import CONFIG
        path = (Path(root) / "data/config/profile.yml") if root else (CONFIG / "profile.yml")
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 - config missing in a bare test workspace
        return {}


def _track_regexes(profile: dict | None = None):
    """Title regex per track (A-D), built from profile.yml role_tracks signals + target titles."""
    profile = _load_profile() if profile is None else profile
    titles = [str(t) for group in ("primary", "secondary") for t in (profile.get("target_roles", {}) or {}).get(group, [])]
    signals = [str(sig) for track in profile.get("role_tracks", []) or [] for sig in track.get("signals", [])]
    words = titles + signals or ["data engineer", "machine learning", "software engineer", "embedded"]
    words += list(RELATED_TITLES)
    return re.compile(r"(?i)\b(?:" + "|".join(re.escape(w) for w in sorted(set(words), key=len, reverse=True)) + r")\b")


# Titles employers use for the same four tracks that the profile's phrases miss. Seen on
# live boards: "SW Test Development Engineer 2" and "Software QA Engineer 2" (Track D test
# automation), "ML Engineer" (Track B), "Software Developer" (Track C). Conservative: each
# names the same day-to-day work; the fit score still decides whether a posting fits.
RELATED_TITLES = (
    "software developer", "software development engineer", "full stack engineer", "full stack developer",
    "software test", "test development engineer", "test automation", "software quality assurance",
    "quality assurance automation", "automation engineer", "validation engineer", "verification engineer",
    "machine learning", "data integration engineer", "bi engineer",
)
_TITLE_ABBREVIATIONS = (
    (re.compile(r"\bSWE\b", re.I), "software engineer"),
    (re.compile(r"\bSDE\b", re.I), "software development engineer"),
    (re.compile(r"\bSW\b", re.I), "software"),
    (re.compile(r"\bML\b"), "machine learning"),
    (re.compile(r"\bQA\b"), "quality assurance"),
    (re.compile(r"\bEngr?\b\.?", re.I), "engineer"),
)


def normalize_title(title: str) -> str:
    """'SW Test Development Engr 2' -> 'software Test Development engineer 2'."""
    text = title or ""
    for pattern, replacement in _TITLE_ABBREVIATIONS:
        text = pattern.sub(replacement, text)
    return text


# The kind of job a title names. The profile's track signals include skills ("warehouse",
# "api", "pipeline") that also appear in unrelated titles ("Warehouse operator", "Account
# Executive, API"), so a title must name the role itself as well.
_ROLE_WORD = re.compile(r"\b(engineer|engineering|developer|scientist|programmer|researcher|sdet|analyst|technologist)\b", re.I)


def title_in_tracks(title: str) -> bool:
    """Whether a job title names one of Annie's four target tracks (seniority is checked separately)."""
    text = normalize_title(title)
    return bool(SUPPORTED_ROLES.search(text)) and bool(_ROLE_WORD.search(text))


SUPPORTED_ROLES = _track_regexes()


class ProfileRules:
    """What one profile's screens read from its own profile.yml, re-read when the file changes."""

    _cache: dict[str, tuple[int, "ProfileRules"]] = {}

    def __init__(self, profile: dict):
        self.roles = _track_regexes(profile)
        targets = profile.get("target_roles") or {}
        self.max_years = int(targets.get("max_years_required") or 4)
        scoring = profile.get("scoring") or {}
        # "Annie holds a Master's": the highest degree, for the PhD blocker's wording.
        self.degree = str(scoring.get("highest_degree") or "a Master's")
        self.name = str((profile.get("candidate") or {}).get("preferred_name") or "").strip() or "The candidate"
        self.role_blocker = str(
            scoring.get("role_blocker")
            or "Role does not match one of the four target families (data, ML/AI, software, embedded/test)."
        )

    @classmethod
    def of(cls, root) -> "ProfileRules":
        path = Path(root) / "data/config/profile.yml"
        try:
            stamp = path.stat().st_mtime_ns
        except OSError:
            stamp = 0
        cached = cls._cache.get(str(path))
        if not cached or cached[0] != stamp:
            cached = (stamp, cls(_load_profile(root)))
            cls._cache[str(path)] = cached
        return cached[1]
CLOSED = re.compile(
    r"\b(job|position|role|vacancy|requisition|posting)\b.{0,55}\b(closed|expired|filled|no longer available|not accepting applications)\b|\bno longer accepting applications\b",
    re.I | re.S,
)
BLOCKED_PAGE = re.compile(r"captcha|verify you are human|access denied|sign in to continue|log in to continue", re.I)
FRAUD = re.compile(
    r"pay(?:ment)? (?:a |the )?(?:fee|deposit)|gift card|crypto(?:currency)? payment|send (?:your )?(?:passport|identity document)|telegram|whatsapp only|personal email address",
    re.I,
)
def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_company(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.casefold())


def company_id(name: str) -> str:
    return "company-" + hashlib.sha256(normalize_company(name).encode()).hexdigest()[:16]


def _host_matches_company(url: str, company: str) -> bool:
    host = (urlsplit(url).hostname or "").casefold().removeprefix("www.")
    if any(host == ats or host.endswith("." + ats) for ats in ATS_DOMAINS):
        return True
    words = [w for w in re.findall(r"[a-z0-9]+", company.casefold()) if len(w) > 2]
    return bool(words) and any(word in host.replace("-", "") for word in words)


class JobQualityService:
    def __init__(self, services, fetcher=None):
        self.s = services
        self.w = services.w
        self.fetcher = fetcher or self._fetch

    @staticmethod
    def _fetch(url: str) -> dict:
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; CareerDashboardVerifier/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        try:
            with urlopen(request, timeout=12) as response:
                body = response.read(750_000).decode(
                    response.headers.get_content_charset() or "utf-8", "replace"
                )
                text = unescape(re.sub(r"<[^>]+>", " ", body))
                return {
                    "status": response.status,
                    "final_url": response.geturl(),
                    "text": re.sub(r"\s+", " ", text)[:250_000],
                }
        except HTTPError as exc:
            return {"status": exc.code, "final_url": exc.geturl(), "text": ""}
        except (URLError, TimeoutError, socket.timeout) as exc:
            return {"status": None, "final_url": url, "text": "", "error": type(exc).__name__}

    def ensure_company(self, name: str) -> str:
        cid = company_id(name)
        with self.w.connect() as db:
            db.execute(
                """INSERT OR IGNORE INTO companies(
                id,normalized_name,display_name,created_at,updated_at)
                VALUES(?,?,?,?,?)""",
                (cid, normalize_company(name), name.strip(), utcnow(), utcnow()),
            )
        return cid

    def verify_posting(self, job_id: str, response: dict | None = None) -> dict:
        job = self.w.get_job(job_id)
        if job.get("record_source") == "gmail":
            raise ValueError("This record has no saved public posting to verify")
        result = response or self.fetcher(job["url"])
        status = result.get("status")
        final_url = result.get("final_url") or job["url"]
        text = str(result.get("text") or "")
        evidence: list[str] = []
        state = "active"
        if status in {404, 410}:
            state = "expired"
            evidence.append(f"Posting returned HTTP {status}.")
        elif status is None:
            state = "needs_review"
            evidence.append(f"Posting could not be checked ({result.get('error', 'network error')}).")
        elif BLOCKED_PAGE.search(text) or status in {401, 403, 429}:
            state = "needs_review"
            evidence.append("The site blocked or gated automated verification.")
        elif CLOSED.search(text):
            state = "expired"
            evidence.append("The retrieved page explicitly says the posting is closed or unavailable.")
        else:
            original = urlsplit(job["url"])
            final = urlsplit(final_url)
            original_parts = [p for p in original.path.split("/") if p]
            generic_redirect = (
                final_url.rstrip("/") != job["url"].rstrip("/")
                and len([p for p in final.path.split("/") if p]) <= 1
                and len(original_parts) >= 2
                and job["title"].casefold() not in text.casefold()
            )
            if generic_redirect:
                state = "expired"
                evidence.append("The exact posting redirects to a generic portal and the role is absent.")
            else:
                evidence.append(f"Posting returned HTTP {status or 200} without closure evidence.")
        # Re-gate the live wording: a posting edited to refuse sponsorship leaves the list for Excluded roles.
        refusal = None
        if state == "active" and text and job["status"] in {"saved", "prepared"}:
            from backend.services import sponsorship
            verdict = self.s.gate(job["company"], text, job["url"], job.get("location", ""))
            if verdict.excluded and not sponsorship.overridden(job.get("sponsor_evidence"), verdict):
                refusal = verdict
                evidence.append(f'The posting now says: "{verdict.screen.sentence}" It moved to Excluded roles.')
        checked = utcnow()
        closed_at = checked if state == "expired" else None
        with self.w.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT INTO posting_checks(job_id,state,http_status,final_url,evidence,checked_at) VALUES(?,?,?,?,?,?)",
                (job_id, state, status, final_url, json.dumps(evidence), checked),
            )
            db.execute(
                "UPDATE jobs SET posting_state=?,last_verified_at=?,closed_at=CASE WHEN ?='expired' THEN ? ELSE NULL END,updated_at=? WHERE id=?",
                (state, checked, state, closed_at, checked, job_id),
            )
            self.w.record_event(
                db, "posting_verified", job_id, state=state, evidence=evidence, final_url=final_url
            )
        if refusal:
            self.s.record_excluded({**job, "description": text}, refusal, source="sweep")
            self.w.remove_job(job_id, "Sponsorship gate: the posting now says: " + refusal.screen.sentence)
        self.s.sync_projections()
        return {"job_id": job_id, "state": state, "checked_at": checked, "final_url": final_url, "evidence": evidence,
                "excluded": bool(refusal)}

    def verify_due(self, hours: int = 24, expired_hours: int = 168) -> dict:
        """Re-check open postings, and expired ones far less often.

        Reads the jobs table directly rather than Workspace.jobs(), which already
        filters expired saved/prepared roles out of the active list: going through
        it meant a posting could never be re-checked once marked expired, so a
        wrongly-closed or reposted role could not recover.
        """
        now = datetime.now(timezone.utc)
        fresh = now - timedelta(hours=hours)
        stale = now - timedelta(hours=expired_hours)
        with self.w.connect() as db:
            rows = db.execute(
                "SELECT id, posting_state, last_verified_at FROM jobs "
                "WHERE deleted_at IS NULL AND status IN ('saved','prepared') "
                "AND COALESCE(record_source,'') <> 'gmail'"
            ).fetchall()
        due = []
        for row in rows:
            checked = row["last_verified_at"]
            threshold = stale if row["posting_state"] == "expired" else fresh
            if not checked or datetime.fromisoformat(checked) <= threshold:
                due.append(row["id"])
        results = [self.verify_posting(job_id) for job_id in due]
        return {"checked": len(results), "results": results}

    def posting_history(self, job_id: str) -> list[dict]:
        with self.w.connect() as db:
            rows = db.execute(
                "SELECT * FROM posting_checks WHERE job_id=? ORDER BY checked_at DESC", (job_id,)
            ).fetchall()
        return [{**dict(row), "evidence": json.loads(row["evidence"])} for row in rows]

    @staticmethod
    def in_target(posting: dict) -> bool:
        """US (or bare Remote) location and an entry-level, full-time title in her tracks."""
        title, location = str(posting.get("title", "")), str(posting.get("location", ""))
        place_ok = is_us_location(location) or re.fullmatch(r"(?i)\s*remote\s*", location or "") is not None
        return place_ok and title_in_tracks(title) and not SENIORITY_BLOCK.search(title) and not INTERNSHIP.search(title)

    def relevance(self, posting: dict, profile_text: str = "") -> dict:
        title = str(posting.get("title", ""))
        location = str(posting.get("location", ""))
        description = str(posting.get("description", ""))
        blockers = []
        # This profile's own country, targets and wording (profile.yml + its country pack).
        from backend.countries import pack_for
        pack = pack_for(self.w.root)
        rules = ProfileRules.of(self.w.root)
        # A bare "Remote" is not a refusal; it earns no location points and gets checked at research time.
        bare_remote = re.fullmatch(r"(?i)\s*remote\s*", location or "") is not None
        if not us_ok and not bare_remote:
            blockers.append("Location is not in the United States (or US-remote). Only US roles are pursued.")
        elif bare_remote and remote_outside_us(description):
            blockers.append("Listed as \"Remote\", but the posting places the work outside the United States. Only US roles are pursued.")
        if SENIORITY_BLOCK.search(title):
            blockers.append("Seniority in the title (Senior/Staff/Lead/Principal/Manager) is outside the entry-level target.")
        if INTERNSHIP.search(title):
            blockers.append("Internships and co-ops are for current students; Annie completed her MS and is looking for a full-time role.")
        if not title_in_tracks(title):
            blockers.append("Role does not match one of the four target families (data, ML/AI, software, embedded/test).")
        years = years_required(description)
        if years and years > rules.max_years:
            blockers.append(f"The posting asks for {years}+ years of experience; the profile caps at {rules.max_years}.")
        if requires_phd(title, description):
            blockers.append("The posting requires a PhD; Annie holds a Master's.")
        elif requires_enrollment(description):
            blockers.append("The posting is for current students (it requires enrollment during the role); Annie completed her MS in May 2026.")
        if len(description.strip()) < 80 or not str(posting.get("url", "")).startswith(("http://", "https://")):
            blockers.append("A full job description and real application route are required.")
        from backend.services.sponsorship import rules_for, screen as sponsorship_screen
        gate = sponsorship_screen(title + "\n" + description, rules_for(self.w.root))
        if gate.verdict == "EXCLUDED":
            blockers.append(f"Sponsorship gate: {gate.reason_label}. Posting says: \"{gate.sentence}\"")
        profile_terms = _terms(profile_text)
        jd_terms = _terms(full)
        overlap = len(profile_terms & jd_terms) / max(1, min(30, len(jd_terms)))
        requirement = min(40, round(overlap * 55))
        role = 25 if title_in_tracks(title) and not SENIORITY_BLOCK.search(title) else 0
        place = 15 if us_ok else 0
        professional_markers = {"python", "sql", "pipeline", "streaming", "pytorch", "aws", "airflow", "kafka", "c++", "c#", "labview", "embedded", "testing"}
        professional = min(15, 3 * len(professional_markers & jd_terms & profile_terms))
        domains = {"medical", "healthcare", "clinical", "device", "insurance", "research", "manufacturing", "iot"}
        domain = min(5, len(domains & jd_terms & profile_terms) * 2)
        score = requirement + role + place + professional + domain
        return {
            "score": score,
            "eligible": eligible,
            "components": analysis["components"],
            "blockers": blockers,
            "why": why,
            "sponsorship": {"verdict": gate.verdict, "reason": gate.reason, "sentence": gate.sentence},
            "threshold": fit.FIT_THRESHOLD,
            "fit": analysis,
        }

    def assess_company(self, company: str, posting_url: str, sources: list[dict], findings: list[str], red_flags: list[str], *, size_category="unknown", employee_min=None, employee_max=None, sponsorship_state="unknown", override_reason="", sync=True) -> dict:
        """``sync=False`` inside a discovery pass, which rebuilds the projections once at its end."""
        cid = self.ensure_company(company)
        source_urls = [str(source.get("url", "")) for source in sources if source.get("url")]
        owned_or_ats = _host_matches_company(posting_url, company)
        # A cited registry or company-page URL is the record itself, so sources count as much as notes.
        legal_presence = any(
            term in " ".join(findings + source_urls).casefold()
            for term in ("company register", "secretary of state", "sec.gov", "edgar", "opencorporates", "legal entity", "trading presence", "registered", "incorporated", "bbb.org", "linkedin.com/company", "crunchbase", "uscis h-1b employer data hub")
        )
        detected = list(red_flags)
        if FRAUD.search(" ".join(findings + red_flags)):
            detected.append("Payment, identity-document or off-channel contact warning detected.")
        if detected:
            state = "blocked"
        elif owned_or_ats and legal_presence and source_urls:
            state = "verified"
        else:
            state = "needs_review"
        if override_reason and state == "needs_review":
            state = "verified"
        checked = utcnow()
        with self.w.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                """UPDATE companies SET website_domain=?,size_category=?,employee_min=?,employee_max=?,
                legitimacy_state=?,sponsorship_state=?,manual_override_reason=?,updated_at=? WHERE id=?""",
                (urlsplit(posting_url).hostname or "", size_category, employee_min, employee_max, state, sponsorship_state, override_reason, checked, cid),
            )
            db.execute(
                "INSERT INTO company_checks(company_id,state,sources,findings,red_flags,checked_at,manual_override,override_reason) VALUES(?,?,?,?,?,?,?,?)",
                (cid, state, json.dumps(sources), json.dumps(findings), json.dumps(detected), checked, int(bool(override_reason)), override_reason),
            )
            db.execute("UPDATE jobs SET company_id=? WHERE lower(replace(company,' ',''))=?", (cid, normalize_company(company)))
            self.w.record_event(db, "company_verified", company_id=cid, company=company, state=state, sources=source_urls)
        if sync:
            self.s.sync_projections()
        return {"company_id": cid, "state": state, "sources": sources, "findings": findings, "red_flags": detected, "checked_at": checked}

    def balanced_five(self, candidates: list[dict], total: int = 5) -> dict:
        """Return an honest 2 startup / 1 mid / 2 large subset, scaled to ``total`` jobs. Mid and large companies must be tier S/A/B (cap-exempt, says yes, or proven sponsor); startups may be tier C.

        That sponsor-record rule needs a sponsor history to check against (the US pack's
        USCIS index). A country without one (Ireland) has no proven-sponsor tier, so there
        the gate's own verdict is the rule: a posting that refuses a permit is already out."""
        from backend.countries import pack_for

        records = bool(pack_for(self.w.root).sponsor_index)
        valid = [
            item for item in candidates
            if item.get("legitimacy_state") == "verified" and item.get("relevance", {}).get("eligible")
        ]
        selected = []
        shortages = []
        startups, mids = round(total * 2 / 5), round(total / 5)
        for category, count, sponsorship_required in (
            ("startup", startups, False), ("mid", mids, records), ("large", total - startups - mids, records)
        ):
            if count <= 0:
                continue
            pool = [
                item for item in valid
                if item.get("size_category") == category
                and (not sponsorship_required or item.get("sponsor_tier") in {"S", "A", "B"})
            ]
            if category == "startup":
                pool = [item for item in pool if self._low_competition(item)]
            selected.extend(pool[:count])
            if len(pool) < count:
                shortages.append({"category": category, "needed": count, "found": len(pool)})
        return {"preset": "balanced_five", "jobs": selected, "complete": not shortages, "shortages": shortages}

    @staticmethod
    def _low_competition(item: dict) -> bool:
        applicants = item.get("applicant_count")
        if isinstance(applicants, int):
            return applicants < 10
        signals = item.get("competition_signals", {})
        count = sum(bool(signals.get(key)) for key in ("posted_within_72h", "limited_syndication", "niche_match"))
        return count >= 2
