"""Deterministic posting freshness, relevance, legitimacy and batch selection."""

from __future__ import annotations

import hashlib
import json
import re
import socket
from datetime import datetime, timedelta, timezone
from html import unescape
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
US_LOCATION = re.compile(
    r"(?i)\b(?:united states|u\.?s\.?a?\.?|usa|us[- ]remote|remote[- ,(]*(?:us|usa|united states)|" + _STATES + "|" + _HUBS + r")\b"
    r"|,\s*(?:" + _ABBR + r")\b(?:\s+\d{5})?\s*(?:,\s*(?:usa?|united states))?$"
    r"|\b(?:" + _ABBR + r")\s+\d{5}\b"
)
# Countries, regions and cities with no US namesake: only a strong US marker outweighs them.
_FOREIGN_STRONG = re.compile(
    r"(?i)\b(?:ireland|united kingdom|uk|canada|toronto|india|bangalore|bengaluru|hyderabad|chennai|pune|germany|france|"
    r"netherlands|spain|poland|singapore|australia|sydney|mexico|brazil|emea|apac|latam|europe)\b"
)
# Cities that also exist in the US (Dublin OH/CA, London KY, Vancouver WA, Paris TX, Berlin NH, Amsterdam NY).
_FOREIGN_TWIN = re.compile(r"(?i)\b(?:dublin|london|vancouver|paris|berlin|amsterdam)\b")
_US_STRONG = re.compile(
    r"(?i)\b(?:united states|u\.s\.a?\.?|usa|us[- ]remote|remote[- ,(]*(?:us|usa|united states)|" + _STATES + r")\b|\b\d{5}(?:-\d{4})?\b"
)
# A trailing two-letter US state. DE and IN are left out: in job feeds they almost always mean Germany and India.
_US_STATE_SUFFIX = re.compile(r",\s*(?:" + "|".join(a for a in _ABBR.split("|") if a not in {"DE", "IN"}) + r")\b")


def is_us_location(location: str) -> bool:
    """True for a US city, state, hub or US-remote location.

    Dublin, OH and Vancouver, WA are American; Dublin, Ireland, Vancouver, BC and
    Bengaluru, IN are not. A posting that offers the US among other countries counts.
    """
    location = location or ""
    if not US_LOCATION.search(location):
        return False
    if _US_STRONG.search(location):
        return True
    if _FOREIGN_STRONG.search(location):
        return False
    return not _FOREIGN_TWIN.search(location) or bool(_US_STATE_SUFFIX.search(location))
SENIORITY_BLOCK = re.compile(r"\b(senior|sr\.?|staff|lead|principal|director|head(?: of)?|manager|architect|distinguished|fellow|vp|vice president)\b", re.I)
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


def _track_regexes():
    """Title regex per track (A-D), built from profile.yml role_tracks signals + target titles."""
    try:
        import yaml
        from backend.paths import CONFIG
        profile = yaml.safe_load((CONFIG / "profile.yml").read_text()) or {}
    except Exception:  # noqa: BLE001 - config missing in a bare test workspace
        profile = {}
    titles = [str(t) for group in ("primary", "secondary") for t in (profile.get("target_roles", {}) or {}).get(group, [])]
    signals = [str(sig) for track in profile.get("role_tracks", []) or [] for sig in track.get("signals", [])]
    words = titles + signals or ["data engineer", "machine learning", "software engineer", "embedded"]
    return re.compile(r"(?i)\b(?:" + "|".join(re.escape(w) for w in sorted(set(words), key=len, reverse=True)) + r")\b")


SUPPORTED_ROLES = _track_regexes()
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


def _terms(text: str) -> set[str]:
    stop = {"and", "the", "with", "for", "from", "that", "this", "your", "our", "you", "are"}
    return {w for w in re.findall(r"[a-z][a-z0-9+#.-]{2,}", text.casefold()) if w not in stop}


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
            verdict = sponsorship.evaluate(job["company"], text, job["url"], job.get("location", ""))
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

    def relevance(self, posting: dict, profile_text: str = "") -> dict:
        title = str(posting.get("title", ""))
        location = str(posting.get("location", ""))
        description = str(posting.get("description", ""))
        full = f"{title}\n{description}"
        blockers = []
        us_ok = is_us_location(location)
        # A bare "Remote" is not a refusal; it earns no location points and gets checked at research time.
        bare_remote = re.fullmatch(r"(?i)\s*remote\s*", location or "") is not None
        if not us_ok and not bare_remote:
            blockers.append("Location is not in the United States (or US-remote). Only US roles are pursued.")
        if SENIORITY_BLOCK.search(title):
            blockers.append("Seniority in the title (Senior/Staff/Lead/Principal/Manager) is outside the entry-level target.")
        if not SUPPORTED_ROLES.search(title):
            blockers.append("Role does not match one of the four target families (data, ML/AI, software, embedded/test).")
        years = years_required(description)
        if years and years > 4:
            blockers.append(f"The posting asks for {years}+ years of experience; the profile caps at 4.")
        if requires_phd(title, description):
            blockers.append("The posting requires a PhD; Annie holds a Master's.")
        if len(description.strip()) < 80 or not str(posting.get("url", "")).startswith(("http://", "https://")):
            blockers.append("A full job description and real application route are required.")
        from backend.services.sponsorship import screen as sponsorship_screen
        gate = sponsorship_screen(full)
        if gate.verdict == "EXCLUDED":
            blockers.append(f"Sponsorship gate: {gate.reason_label}. Posting says: \"{gate.sentence}\"")
        profile_terms = _terms(profile_text)
        jd_terms = _terms(full)
        overlap = len(profile_terms & jd_terms) / max(1, min(30, len(jd_terms)))
        requirement = min(40, round(overlap * 55))
        role = 25 if SUPPORTED_ROLES.search(title) and not SENIORITY_BLOCK.search(title) else 0
        place = 15 if us_ok else 0
        professional_markers = {"python", "sql", "pipeline", "streaming", "pytorch", "aws", "airflow", "kafka", "c++", "c#", "labview", "embedded", "testing"}
        professional = min(15, 3 * len(professional_markers & jd_terms & profile_terms))
        domains = {"medical", "healthcare", "clinical", "device", "insurance", "research", "manufacturing", "iot"}
        domain = min(5, len(domains & jd_terms & profile_terms) * 2)
        score = requirement + role + place + professional + domain
        return {
            "score": score,
            "eligible": not blockers and score >= 70,
            "components": {
                "requirement_evidence": requirement,
                "role_seniority": role,
                "location": place,
                "professional_fit": professional,
                "domain": domain,
            },
            "blockers": blockers,
            "sponsorship": {"verdict": gate.verdict, "reason": gate.reason, "sentence": gate.sentence},
            "threshold": 70,
        }

    def assess_company(self, company: str, posting_url: str, sources: list[dict], findings: list[str], red_flags: list[str], *, size_category="unknown", employee_min=None, employee_max=None, sponsorship_state="unknown", override_reason="") -> dict:
        cid = self.ensure_company(company)
        source_urls = [str(source.get("url", "")) for source in sources if source.get("url")]
        owned_or_ats = _host_matches_company(posting_url, company)
        legal_presence = any(
            term in " ".join(findings).casefold()
            for term in ("company register", "secretary of state", "sec.gov", "edgar", "opencorporates", "legal entity", "trading presence", "registered", "incorporated", "bbb.org", "linkedin.com/company", "crunchbase")
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
        self.s.sync_projections()
        return {"company_id": cid, "state": state, "sources": sources, "findings": findings, "red_flags": detected, "checked_at": checked}

    def balanced_five(self, candidates: list[dict]) -> dict:
        """Return an honest 2 startup / 1 mid / 2 large subset. Mid and large companies must be tier S/A/B (cap-exempt, says yes, or proven sponsor); startups may be tier C."""
        valid = [
            item for item in candidates
            if item.get("legitimacy_state") == "verified" and item.get("relevance", {}).get("eligible")
        ]
        selected = []
        shortages = []
        for category, count, sponsorship_required in (
            ("startup", 2, False), ("mid", 1, True), ("large", 2, True)
        ):
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
