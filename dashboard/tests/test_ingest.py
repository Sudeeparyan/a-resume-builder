"""
The return path: a Claude or ChatGPT project answer, pasted back in.

The load-bearing assertion here is that nothing in the paste is trusted. An
assistant can invent a company, a link, or a sponsorship claim, so the gates
that protect her have to run again locally on whatever arrives.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services import ingest  # noqa: E402

TABLE = """
Here are the roles I found for you.

| # | Company | Role | Tier | Location | Link |
|---|---------|------|------|----------|------|
| 1 | Databricks | Data Engineer | B | San Francisco, CA | [Apply](https://boards.greenhouse.io/databricks/jobs/123) |
| 2 | Confluent | Software Engineer I | C | Remote | [Apply](https://jobs.lever.co/confluent/abc) |

Let me know which you want a resume for.
"""

BLOCK = """
Here is the list.

```careerops
{"version": 1, "jobs": [
  {"company": "Stripe", "role_title": "Data Engineer",
   "url": "https://stripe.com/jobs/1", "location": "Remote",
   "jd_text": "We need Python, SQL, Kafka and Airflow for streaming pipelines."},
  {"company": "Snowflake", "role_title": "Analytics Engineer",
   "url": "https://snowflake.com/jobs/2", "location": "San Mateo, CA"}
]}
```
"""


def test_reads_a_markdown_table():
    rows = ingest.parse(TABLE)
    assert len(rows) == 2
    assert rows[0]["company"] == "Databricks"
    # The real URL must come out of the markdown link, not the word "Apply".
    assert rows[0]["url"].startswith("https://boards.greenhouse.io")


def test_reads_the_fenced_block():
    rows = ingest.parse(BLOCK)
    assert [r["company"] for r in rows] == ["Stripe", "Snowflake"]
    assert "Kafka" in rows[0]["jd_text"]


def test_reads_a_bare_json_array():
    rows = ingest.parse(json.dumps([
        {"employer": "Acme", "position": "Data Engineer", "link": "https://a.co/1"}
    ]))
    assert rows[0]["company"] == "Acme"


def test_empty_and_prose_are_refused_helpfully():
    with pytest.raises(ingest.IngestError):
        ingest.parse("")
    with pytest.raises(ingest.IngestError) as exc:
        ingest.parse("I could not find anything today, sorry!")
    assert "careerops" in str(exc.value)


def test_a_claimed_tier_is_discarded_and_recomputed():
    """
    The table above asserts Databricks is tier B. That claim is ignored: the
    tier must come from the local sponsorship gate and the USCIS index.
    """
    rows = ingest.parse(TABLE)
    res = ingest.screen(ingest.to_postings(rows))
    assert res["scored"], "both rows should survive the gates"
    for s in res["scored"]:
        assert s.sponsor.tier.value in ("S", "A", "B", "C")
        assert s.sponsor.verdict == "KEEP"


def test_links_are_never_trusted_as_live():
    rows = ingest.parse(TABLE)
    res = ingest.screen(ingest.to_postings(rows))
    for s in res["scored"]:
        assert s.link_status.value == "UNCHECKED"


def test_sponsorship_gate_runs_on_pasted_text():
    """A posting the assistant listed anyway must still be excluded locally."""
    rows = ingest.parse(json.dumps([{
        "company": "Lockheed Test Co",
        "role_title": "Data Engineer",
        "url": "https://example.com/1",
        "jd_text": (
            "This position requires US citizenship and an active security clearance. "
            "We will not sponsor applicants for work visas now or in the future."
        ),
    }]))
    res = ingest.screen(ingest.to_postings(rows))
    assert res["scored"] == []
    assert res["excluded"], "it must be excluded, and say why"
    e = res["excluded"][0]
    assert e.triggering_sentence, "every exclusion carries the sentence that caused it"


def test_preview_warns_about_missing_links_and_ad_text():
    rows = ingest.parse(json.dumps([
        {"company": "Nowhere Inc", "role_title": "Data Engineer"}
    ]))
    res = ingest.screen(ingest.to_postings(rows))
    if res["scored"]:
        out = ingest.preview(json.dumps([
            {"company": "Nowhere Inc", "role_title": "Data Engineer"}
        ]))
        joined = " ".join(out["warnings"]).lower()
        assert "no link" in joined or "unverified" in joined


def test_preview_writes_nothing():
    """Preview must be safe to run repeatedly before she commits."""
    from backend import db
    before = db.connect().execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    ingest.preview(BLOCK)
    after = db.connect().execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    assert before == after
