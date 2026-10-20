"""The US sponsorship upgrade: H-1B sponsor boards, the Sponsorship Tracker, removal lessons.

Ported in spirit from the template edition's Irish permit-employer registry and Tracker:
* the careers boards of employers in the USCIS H-1B data are found, checked to name the same
  employer, and read by the no-AI feed pass on rotation;
* every in-target posting a pass reads is kept with its quoted sponsorship sentence, H-1B
  record, pay and the gate that decided it;
* removing a role as "Not this company" / "This company won't sponsor me" / "Wrong kind of
  role" teaches automatic searches to skip that company or title.
No network: board responses are recorded here.
"""

import csv
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from backend.dashboard.app import create_app  # noqa: E402
from backend.services import market_tracker, portals, reapply, sponsor_boards, sponsorship  # noqa: E402
from backend.services.agents import AgentRunner  # noqa: E402
from test_career_workspace import workspace, JD  # noqa: E402,F401
from test_workspace_v2 import service  # noqa: E402,F401

DESCRIPTION = ("Build Python and SQL data pipelines on AWS with Airflow and Kafka streaming; validate device telemetry, "
               "write automated tests and maintain ETL jobs for clinical dashboards. Bachelor's or Master's degree. "
               "Python SQL Kafka Airflow pipeline streaming testing.")


# ---- names and board checks ------------------------------------------------------------------

def test_slug_guesses_come_from_the_brand_not_the_legal_form():
    assert sponsor_boards.slug_variants("STRIPE INC") == ["stripe"]
    assert sponsor_boards.slug_variants("ROBINHOOD MARKETS INC") == ["robinhood", "robinhoodmarkets"]
    assert sponsor_boards.slug_variants("PALO ALTO NETWORKS INC") == ["paloalto", "palo-alto", "paloaltonetworks"]
    assert sponsor_boards.slug_variants("PALANTIR TECHNOLOGIES INC") == ["palantir"]
    # A generic first word is never a board on its own.
    assert "global" not in sponsor_boards.slug_variants("GLOBAL DATA SERVICES LLC")
    assert sponsor_boards.slug_variants("US INC") == []


def test_a_board_must_name_the_same_employer():
    assert sponsor_boards.name_match("Stripe", "STRIPE INC") == "exact"
    assert sponsor_boards.name_match("Careers at DoorDash USA", "DOORDASH INC") == "exact"
    assert sponsor_boards.name_match("Robinhood", "ROBINHOOD MARKETS INC") == "brand"
    assert sponsor_boards.name_match("Datadogg", "DATADOG INC") == "similar"
    assert sponsor_boards.name_match("Apple Leisure Group", "APPLE INC") == ""
    assert sponsor_boards.name_match("American Express", "AMERICAN AIRLINES INC") == ""
    # Posting text is the check when a board states no name: a distinctive brand only.
    assert sponsor_boards.named_in_text(["Plaid is hiring in New York"], "PLAID INC")
    assert not sponsor_boards.named_in_text(["Join the ramp team"], "RAMP SYSTEMS INC")  # too short to prove anything


def fake_api(responses):
    def get_json(url, body=None):
        for marker, answer in responses.items():
            if marker in url:
                return answer
        return None, "HTTP 404"
    return get_json


def test_resolve_accepts_only_a_named_board_with_a_us_posting():
    get_json = fake_api({
        "greenhouse.io/v1/boards/stripe/jobs": ({"jobs": [{"title": "Software Engineer, New Grad", "location": {"name": "Seattle, WA"}},
                                                          {"title": "Account Executive", "location": {"name": "Dublin, Ireland"}}]}, None),
        "greenhouse.io/v1/boards/stripe": ({"name": "Stripe"}, None),
    })
    found = sponsor_boards.resolve("STRIPE INC", get_json)
    assert found["status"] == "resolved" and (found["ats"], found["token"]) == ("greenhouse", "stripe")
    assert found["us_postings"] == 1 and found["target_postings"] == 1 and found["match"] == "exact"

    abroad = fake_api({"api.lever.co/v0/postings/acmeanalytics": ([{"text": "Data Engineer", "categories": {"location": "London, UK"},
                                                                     "country": "GB", "descriptionPlain": "Acme Analytics"}], None)})
    refused = sponsor_boards.resolve("ACME ANALYTICS INC", abroad)
    assert refused["status"] == "unresolved"
    assert refused["refused"][0]["reason"] == "no current posting in the United States"

    other = fake_api({"greenhouse.io/v1/boards/apple/jobs": ({"jobs": [{"title": "Analyst", "location": {"name": "Austin, TX"}}]}, None),
                      "greenhouse.io/v1/boards/apple": ({"name": "Apple Leisure Group"}, None)})
    assert sponsor_boards.resolve("APPLE INC", other)["status"] == "unresolved"


def write_registry(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sponsor_boards.write([{**{f: "" for f in sponsor_boards.FIELDS}, **row} for row in rows], path)
    return path


ROBINHOOD = {"employer": "Robinhood", "legal_name": "ROBINHOOD MARKETS INC", "employer_key": "robinhood markets",
             "ats": "greenhouse", "token": "robinhood", "h1b_approvals": "540", "h1b_denials": "12",
             "fiscal_years": "2021;2022;2023", "us_postings": "134", "target_postings": "4",
             "name_check": "board name: Robinhood (brand)", "verified_on": "2026-10-08"}


def test_a_brand_name_finds_its_uscis_record_through_the_registry(tmp_path, monkeypatch):
    path = write_registry(tmp_path / "sponsor-boards.csv", [ROBINHOOD])
    monkeypatch.setattr(sponsor_boards, "BOARDS_CSV", path)
    if not sponsorship.index().lookup("robinhood markets")["found"]:
        pytest.skip("USCIS data not present in this copy")
    verdict = sponsorship.evaluate("Robinhood", DESCRIPTION, "https://boards.greenhouse.io/robinhood/jobs/1", "Menlo Park, CA")
    assert verdict.tier == "B" and verdict.h1b_approvals > 0 and verdict.h1b_denials >= 0
    assert verdict.h1b_matched_name == "ROBINHOOD MARKETS INC"


def test_due_rows_rotate_skip_tracked_employers_and_rest_gone_boards(service, tmp_path):
    other = {**ROBINHOOD, "employer": "Plaid", "legal_name": "PLAID INC", "employer_key": "plaid", "ats": "ashby",
             "token": "plaid", "h1b_approvals": "126"}
    tracked = {**ROBINHOOD, "employer": "Stripe", "legal_name": "STRIPE INC", "employer_key": "stripe", "token": "stripe"}
    path = write_registry(tmp_path / "boards.csv", [ROBINHOOD, other, tracked])
    with service.w.connect() as db:
        first = sponsor_boards.due_rows(db, limit=5, skip_names={"Stripe"}, path=path)
        assert [r["name"] for r in first] == ["Robinhood", "Plaid"]  # never read: larger sponsor first
        assert first[0]["_source"] == "sponsor_board" and "USCIS H-1B" in first[0]["_vouched"]
        assert first[0]["careers_url"] == "https://job-boards.greenhouse.io/robinhood"
        sponsor_boards.record_reads(db, [(first[0], 12, None), (first[1], 0, "HTTP 404")])
        again = sponsor_boards.due_rows(db, limit=5, skip_names={"Stripe"}, path=path)
        assert [r["name"] for r in again] == ["Robinhood"]  # Plaid's board is gone for now
        assert sponsor_boards.stats(db, path)["read_ever"] == 2


# ---- the Tracker -----------------------------------------------------------------------------

def test_pay_ranges_are_read_as_annual_dollars():
    assert market_tracker.pay_range("The base salary range is $95,000 - $125,000 per year.")[:2] == (95000, 125000)
    assert market_tracker.pay_range("Pay: $110k–$140k plus equity")[:2] == (110000, 140000)
    assert market_tracker.pay_range("$40 - $55 per hour")[:2] == (83200, 114400)
    assert market_tracker.pay_range("$120,000 to 150,000 USD")[:2] == (120000, 150000)
    assert market_tracker.pay_range("We raised $50M - $100M in funding")[:2] == (None, None)
    assert market_tracker.pay_range("No numbers here") == (None, None, "")


def observe(company, title, url, text, source="tracked", location="Austin, TX"):
    job = {"company": company, "title": title, "url": url, "location": location, "description": text}
    return market_tracker.observation(job, sponsorship.evaluate(company, text, url, location), source)


def test_tracker_rows_quote_the_sentence_filter_and_export(service):
    silent = observe("Acme Analytics", "Data Engineer", "https://acme.test/jobs/1", DESCRIPTION + " Salary $90,000 - $120,000.")
    yes = observe("Beta Health", "ML Engineer", "https://beta.test/jobs/2", DESCRIPTION + " Visa sponsorship is available for this role.")
    no = observe("Gamma Corp", "Software Engineer", "https://gamma.test/jobs/3", DESCRIPTION + " We are unable to provide visa sponsorship.")
    silent.update(outcome="relevance", outcome_reason="Fit 55/100", fit_score=55)
    with service.w.connect() as db:
        assert market_tracker.record(db, [silent, yes, no, None]) == 3
        first_seen = db.execute("SELECT first_seen FROM market_postings WHERE key=?", (silent["key"],)).fetchone()[0]
        market_tracker.record(db, [{**silent, "outcome": "not_selected"}])
        row = db.execute("SELECT first_seen, times_seen, outcome FROM market_postings WHERE key=?", (silent["key"],)).fetchone()
        assert tuple(row) == (first_seen, 2, "not_selected")  # first sighting kept, latest decision wins

        shown = market_tracker.query(db)
        assert [item["company"] for item in shown["items"]] == ["Beta Health", "Acme Analytics"]  # A before C; refusal hidden
        assert shown["summary"]["refusing"] == 1 and shown["summary"]["says_sponsors"] == 1
        assert shown["items"][0]["statement_label"] == "Says it sponsors" and "sponsorship is available" in shown["items"][0]["sentence"]
        refusing = market_tracker.query(db, {"statement": "refuses"})["items"]
        assert [item["company"] for item in refusing] == ["Gamma Corp"] and "unable to provide" in refusing[0]["sentence"]
        assert [i["company"] for i in market_tracker.query(db, {"min_pay": "100000"})["items"]] == ["Acme Analytics"]
        text = market_tracker.to_csv(market_tracker.rows_for_export(db, {"hide_refusing": "0"}))
    lines = list(csv.reader(text.splitlines()))
    assert lines[0][:3] == ["Company", "Role", "Location"] and len(lines) == 4


def test_tracker_api_lists_exports_and_saves_through_the_gates(service):
    silent = observe("Acme Analytics", "Data Engineer", "https://acme.test/jobs/1", JD)
    refusing = observe("Gamma Corp", "Software Engineer", "https://gamma.test/jobs/3", JD + " We are unable to provide visa sponsorship.")
    with service.w.connect() as db:
        market_tracker.record(db, [silent, refusing])
    with TestClient(create_app(service.w.root), base_url="http://127.0.0.1") as client:
        listed = client.get("/api/v2/tracker").json()
        assert [item["company"] for item in listed["items"]] == ["Acme Analytics"] and listed["items"][0]["mine"] == ""
        assert "sponsor_boards" in listed
        exported = client.get("/api/v2/tracker.csv?hide_refusing=0")
        assert exported.status_code == 200 and "text/csv" in exported.headers["content-type"]
        assert "Gamma Corp" in exported.text
        saved = client.post("/api/v2/tracker/save", json={"key": silent["key"]}).json()
        assert saved["job"]["company"] == "Acme Analytics"
        after = client.get("/api/v2/tracker").json()["items"][0]
        assert after["mine"] == "saved" and after["outcome"] == "saved"
        refused = client.post("/api/v2/tracker/save", json={"key": refusing["key"]})
        assert refused.status_code == 400 and "exclude" in refused.json()["detail"]


# ---- removal lessons ---------------------------------------------------------------------------

def removed(company, title, reason):
    return {"company": company, "title": title, "status": "saved", "deleted_at": "2026-10-01T00:00:00+00:00",
            "deletion_reason": reason, "updated_at": "2026-10-01T00:00:00+00:00", "url": "https://x.test/1"}


def test_removal_reasons_teach_automatic_searches_only():
    company = [removed("Acme", "Data Engineer", "Not this company: bad reviews")]
    assert reapply.check("Acme", "ML Engineer", company)["rule"] == "removed_company"
    assert reapply.check("Acme", "ML Engineer", [removed("Acme", "Data Engineer", "This company won't sponsor me")])["rule"] == "removed_company"
    title = [removed("Acme", "Test Engineer", "Wrong kind of role")]
    assert reapply.check("Beta", "Test Engineer", title)["rule"] == "removed_title"
    assert not reapply.check("Beta", "Data Engineer", title)["blocked"]
    # Seniority, location and a gate's own removal belong to that vacancy only.
    for reason in ("Too senior for me", "Wrong location", "Not suitable", "Sponsorship gate: Posting explicitly will not sponsor"):
        assert not reapply.check("Acme", "ML Engineer", [removed("Acme", "Data Engineer", reason)])["blocked"], reason
    # A job Annie saves herself is never blocked by a lesson; it carries a note.
    manual = reapply.check("Acme", "ML Engineer", company, learn=False)
    assert not manual["blocked"] and "automatic searches skip" in manual["note"]


def test_a_removed_company_stays_out_of_discovery_but_not_out_of_her_own_saves(service):
    first = service.add_posting({"company": "Acme Analytics", "title": "Data Engineer", "location": "Austin, TX",
                                 "url": "https://acme.test/jobs/1", "description": JD}, source="manual")
    service.remove_job(first["job"]["id"], "Not this company")
    other = {"company": "Acme Analytics", "title": "ML Engineer", "location": "Austin, TX",
             "url": "https://acme.test/jobs/2", "description": JD}
    blocked = service.add_posting(other, source="discovery")
    assert blocked["blocked"] and blocked["rule"] == "removed_company"
    mine = service.add_posting(other, source="manual")
    assert mine["job"] and "automatic searches skip" in (mine["job"].get("notes") or "")


# ---- the feed pass end to end ------------------------------------------------------------------

def test_the_feed_pass_reads_sponsor_boards_and_fills_the_tracker(service, monkeypatch):
    path = write_registry(service.w.root / "data/sponsors/sponsor-boards.csv", [ROBINHOOD])
    monkeypatch.setattr(sponsor_boards, "BOARDS_CSV", path)
    tracked = {"name": "Dexcom", "careers_url": "https://boards.greenhouse.io/dexcom"}
    good = portals._posting(tracked, "1", "Data Engineer", "https://boards.greenhouse.io/dexcom/jobs/1", "San Diego, CA", DESCRIPTION)
    refusing = portals._posting(tracked, "2", "Software Engineer", "https://boards.greenhouse.io/dexcom/jobs/2", "San Diego, CA",
                                DESCRIPTION + " We are unable to provide visa sponsorship.")
    monkeypatch.setattr(portals, "fetch_all", lambda *a, **k: ([good, refusing], ["Dexcom: 2 open postings via greenhouse"]))
    read_rows = []

    def fetch_rows(rows, *a, **k):
        read_rows.extend(rows)
        out = []
        for row in rows:
            posting = portals._posting(row, "77", "Software Engineer, Data", "https://boards.greenhouse.io/robinhood/jobs/77",
                                       "Menlo Park, CA", DESCRIPTION + " The salary range is $120,000 - $150,000.")
            out.append((row, [posting], None, f"{row['name']}: 1 open postings via greenhouse"))
        return out

    monkeypatch.setattr(portals, "fetch_rows", fetch_rows)
    runner = AgentRunner(service, lambda *a, **kw: pytest.fail("the portals preset must never call the AI"))
    runner.enqueue("discovery", preset="portals")
    runner.pool.shutdown(wait=True)
    run = service.runs()[0]
    assert run["state"] == "completed", run["error"]
    assert [r["name"] for r in read_rows] == ["Robinhood"]
    assert "H-1B sponsor boards: read 1 of 1" in run["result"]["summary"]
    assert run["result"]["tracker_rows"] == 3
    with service.w.connect() as db:
        rows = {r["company"] + "/" + r["title"]: r for r in market_tracker.query(db, {"hide_refusing": "0"})["items"]}
        reads = db.execute("SELECT board, postings FROM sponsor_board_reads").fetchall()
    assert [tuple(r) for r in reads] == [("greenhouse:robinhood", 1)]
    board_row = rows["Robinhood/Software Engineer, Data"]
    assert board_row["source"] == "sponsor_board" and board_row["pay_min"] == 120000
    assert board_row["outcome"] in ("saved", "relevance", "not_selected")
    assert rows["Dexcom/Software Engineer"]["outcome"] == "excluded" and "unable to provide" in rows["Dexcom/Software Engineer"]["sentence"]
    # Run records still carry no posting texts or private bookkeeping.
    assert all("_seen" not in job and "_vouched" not in job and "description" not in job for job in run["result"]["jobs"])


# ---- building the registry -----------------------------------------------------------------------

def test_an_interrupted_build_resumes_from_its_checkpoint(tmp_path, monkeypatch):
    import json

    sys.path.insert(0, str(ROOT / "backend/scripts"))
    import build_sponsor_boards as builder

    pool = [{"employer_key": key, "legal_name": name, "h1b_approvals": n, "h1b_denials": 0, "fiscal_years": "2023"}
            for key, name, n in (("stripe", "STRIPE INC", 664), ("plaid", "PLAID INC", 126), ("acme", "ACME INC", 50))]
    monkeypatch.setattr(sponsor_boards, "candidates", lambda *a, **k: list(pool))
    monkeypatch.setattr(builder, "tracked_keys", lambda: set())
    asked = []

    def resolve(legal_name, *a, **k):
        asked.append(legal_name)
        if legal_name == "PLAID INC":
            return {"status": "resolved", "legal_name": legal_name, "ats": "ashby", "token": "plaid", "board_name": "",
                    "match": "text", "reason": "a US posting's own text names the employer", "us_postings": 9,
                    "target_postings": 2}
        return {"status": "unresolved", "legal_name": legal_name, "tried": [], "refused": []}

    monkeypatch.setattr(sponsor_boards, "resolve", resolve)
    output = tmp_path / "sponsor-boards.csv"
    stripe = {"status": "resolved", "legal_name": "STRIPE INC", "ats": "greenhouse", "token": "stripe", "board_name": "Stripe",
              "match": "exact", "reason": "board name: Stripe (exact)", "us_postings": 300, "target_postings": 20}
    progress = tmp_path / "sponsor-boards-progress.json"
    progress.write_text(json.dumps({"results": {"STRIPE INC": {**stripe, "h1b_approvals": 664}},
                                    "accepted": [sponsor_boards.registry_row(stripe, pool[0], "2026-10-09")]}))
    assert builder.main(["--resume", "--output", str(output), "--workers", "1"]) == 0
    assert asked == ["PLAID INC", "ACME INC"]  # Stripe was decided before the interruption
    assert [r["employer"] for r in sponsor_boards.load(output)] == ["Stripe", "Plaid"]
    assert not progress.exists() and (tmp_path / "sponsor-boards.meta.yml").is_file()


def test_a_one_word_brand_must_also_hire_where_uscis_records_the_employer():
    assert sponsor_boards.needs_place_check("MERCURY SYSTEMS INC")      # "mercury" alone is anyone's name
    assert sponsor_boards.needs_place_check("ROBINHOOD MARKETS INC")
    assert not sponsor_boards.needs_place_check("ROBLOX CORPORATION")   # only a legal form was dropped
    assert not sponsor_boards.needs_place_check("JANE STREET GROUP LLC")  # two words stay distinctive
    assert sponsor_boards.in_place("Andover, MA", "MA", "ANDOVER") and sponsor_boards.in_place("Austin, Texas", "TX", "")
    assert not sponsor_boards.in_place("Remote or hybrid, US", "OR", "")  # "or" is not Oregon
    fintech = {"ats": "greenhouse", "token": "mercury", "name": "Mercury", "error": None,
               "postings": [{"title": "Software Engineer", "location": "San Francisco, CA", "us": True, "text": ""}]}
    refused = sponsor_boards.judge(fintech, "MERCURY SYSTEMS INC", "MA", "ANDOVER")
    assert not refused["accepted"] and "Andover, MA" in refused["reason"]
    same = {**fintech, "postings": [{"title": "Software Engineer", "location": "Andover, MA", "us": True, "text": ""}]}
    assert sponsor_boards.judge(same, "MERCURY SYSTEMS INC", "MA", "ANDOVER")["accepted"]
    # Without a USCIS place (older data) the name check alone decides, as before.
    assert sponsor_boards.judge(fintech, "MERCURY SYSTEMS INC")["accepted"]


# ---- the 2026-10-09 audit: only US roles, and every refusal wording ---------------------------

REFUSALS = [
    "Not open to candidates who require sponsorship.",
    "This role does not qualify for immigration sponsorship.",
    "We are unable to consider candidates who will require visa sponsorship.",
    "This position requires access to export-controlled information; candidates must be U.S. persons.",
    "Candidates must be able to work in the US without H-1B sponsorship.",
    "Sponsorship not available.",
    "Candidates who now or in the future require sponsorship need not apply.",
    "Must have permanent work authorization in the United States.",
    "OPT/CPT candidates will not be considered.",
    "We do not accept candidates on OPT, CPT or H-1B visas.",
    "Visa sponsorship: No",
    "Sponsorship: Not available",
    "This role is not open to visa sponsorship.",
    "The company will not consider candidates who require sponsorship for a work-authorized visa.",
]
HARMLESS = [
    "Must be authorized to work in the United States.",
    "Will you now or in the future require sponsorship for employment visa status?",
    "Do you require sponsorship: Yes / No",
    "No security clearance required.",
    "We welcome candidates on OPT and STEM OPT.",
    "You will partner with an executive sponsor on each project.",
    "All qualified applicants will receive consideration without regard to national origin or citizenship status.",
]


@pytest.mark.parametrize("sentence", REFUSALS)
def test_every_common_refusal_wording_excludes(sentence):
    assert sponsorship.screen(DESCRIPTION + "\n" + sentence).verdict == "EXCLUDED"


@pytest.mark.parametrize("sentence", HARMLESS)
def test_harmless_wording_never_excludes(sentence):
    assert sponsorship.screen(DESCRIPTION + "\n" + sentence).verdict == "KEEP"


def test_country_codes_that_look_like_states_are_not_american():
    from backend.job_quality import is_us_location
    for place in ("Indianapolis, IN", "Warsaw, IN", "Wilmington, DE", "Chicago, IL", "Denver, CO", "Ontario, CA",
                  "Geneva, IL", "San Francisco, CA; Toronto, ON", "Austin, TX or Remote, Canada", "Athens, GA"):
        assert is_us_location(place), place
    for place in ("Mumbai, IN", "Vellore, IN", "Munich, DE", "Leipzig, DE", "Tel Aviv, IL", "Montreal, CA",
                  "Bogota, CO", "Buenos Aires, AR", "Jakarta, ID", "Tbilisi, Georgia", "Delhi, IN", "Remote - EMEA"):
        assert not is_us_location(place), place


def test_a_bare_remote_role_placed_abroad_is_not_hers(service):
    from backend.job_quality import JobQualityService, remote_outside_us
    assert remote_outside_us("This is a fully remote role for candidates based in Canada.")
    assert not remote_outside_us("Remote within the United States. We also have offices in London.")
    assert not remote_outside_us(DESCRIPTION)
    abroad = {"company": "Acme Analytics", "title": "Data Engineer", "url": "https://acme.test/jobs/abroad",
              "location": "Remote", "description": DESCRIPTION + " You will work remotely from Canada."}
    blockers = JobQualityService(service).relevance(abroad, DESCRIPTION)["blockers"]
    assert any("outside the United States" in blocker for blocker in blockers)
    home = {**abroad, "description": DESCRIPTION}
    assert not any("United States" in blocker for blocker in JobQualityService(service).relevance(home, DESCRIPTION)["blockers"])
    assert service.add_posting(abroad)["rule"] == "outside_us"


def test_a_role_outside_the_us_is_never_saved_or_tracked(service):
    foreign = {"company": "Acme Analytics", "title": "Data Engineer", "location": "Mumbai, IN",
               "url": "https://acme.test/jobs/mumbai", "description": DESCRIPTION}
    result = service.add_posting(foreign)
    assert result["blocked"] and result["rule"] == "outside_us" and not service.w.jobs()
    assert observe("Acme Analytics", "Data Engineer", "https://acme.test/jobs/mumbai", DESCRIPTION, location="Mumbai, IN") is None
    assert observe("Acme Analytics", "Data Engineer", "https://acme.test/jobs/austin", DESCRIPTION) is not None
    assert service.add_posting({**foreign, "location": "Austin, TX", "url": "https://acme.test/jobs/austin"})["job"]
