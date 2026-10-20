"""Cover letters from Annie's registered evidence only, checked before they are saved, with Word copies.

Ported from the Template's tests (October 2026) onto Annie's own registry: a stub plays the
writer and the auditor, so no AI app is reached.
"""

from __future__ import annotations

import io
import json
import re

import pytest
from docx import Document

from test_career_workspace import JD, add, workspace  # noqa: F401 - fixture
from test_workspace_v2 import service  # noqa: F401 - fixture

from backend.services import cover_letters, docx_export, fit
from backend.services.resume_studio import ResumeStudio

NAME = "Annie Prasanna Manoharan"


class StubWriter:
    """The writer and its auditor: returns the drafts given, in order, keeps every payload,
    and audits with the verdicts given (no unsupported sentence once they run out)."""
    served = ("kimi_cli", "kimi-runtime")

    def __init__(self, *drafts, audits=()):
        self.drafts, self.payloads, self.audits, self.audited = list(drafts), [], list(audits), []

    def run(self, name, payload):
        if name == "letter_auditor":
            self.audited.append(payload)
            verdict = self.audits.pop(0) if self.audits else {"unsupported": []}
            if isinstance(verdict, Exception):
                raise verdict
            return verdict
        assert name == "cover_letter_writer"
        self.payloads.append(payload)
        return self.drafts.pop(0)


def facts_of(service, evidence_id):
    entry = next(e for e in fit.catalogue(service)["entries"] if e["id"] == evidence_id)
    return entry["text"].split(": ", 1)[1]


def good_draft(service, job):
    """A body built only from her registered wording, citing where each part came from."""
    work = facts_of(service, "EXP-INSOPS-001")
    project = facts_of(service, "PROJ-P01-IOT")
    body = "\n\n".join([
        f"I am applying for the {job['title']} role at {job['company']}. In my current role, {work[0].lower() + work[1:]}",
        f"I also built a streaming analytics project. {project}",
        f"Thank you for considering my application. I would welcome a conversation about the {job['title']} role "
        f"and how this work could help your team.",
    ])
    return {"body": body, "evidence_ids": ["EXP-INSOPS-001", "PROJ-P01-IOT"], "unsupported_claims": []}


def test_without_ai_the_letter_uses_her_registered_sentences(service):
    job = add(service.w)
    letter = service.generate_cover_letter(job["id"])
    assert letter["method"] == "template" and letter["version"] == 1
    lines = letter["content"].splitlines()
    assert lines[0] == NAME and "Dear Hiring Team," in lines
    assert letter["content"].rstrip().endswith("Sincerely,\n" + NAME)
    assert any(re.fullmatch(r"[A-Z][a-z]+ \d{1,2}, \d{4}", line) for line in lines), "a US-style date"
    assert not cover_letters.IMMIGRATION.search(letter["content"])
    for banned in ("years of experience", "ICCV", "Ireland"):
        assert banned not in letter["content"]
    saved = json.loads((service.w.root / "data/output" / letter["path"].replace(".md", ".json")).read_text(encoding="utf-8"))
    known = {e["id"] for e in fit.catalogue(service)["entries"]} | {c["id"] for c in service.w.evidence()["claims"]}
    assert set(saved["evidence_ids"]) <= known and saved["method"] == "template"
    assert (service.w.root / "data/output" / letter["docx_path"]).is_file()
    assert service.generate_cover_letter(job["id"])["version"] == 2


def test_an_ai_draft_that_passes_every_check_is_used(service):
    job = add(service.w)
    draft = good_draft(service, job)
    cat, matrix = fit.catalogue(service), fit.for_job(service, job["id"], use_ai=False)["matrix"]
    assert cover_letters.check(draft, job=job, cat=cat, matrix=matrix, facts=[]) == []
    writer = StubWriter(draft)
    letter = service.generate_cover_letter(job["id"], team=writer)
    assert letter["method"] == "ai" and letter["provider"] == "kimi_cli", letter["note"]
    assert draft["body"].split("\n\n")[0] in letter["content"]
    assert {"EXP-INSOPS-001", "PROJ-P01-IOT"} <= set(letter["evidence_ids"])
    sent = writer.payloads[0]
    assert sent["company_facts"] == [] and "H-1B" in sent["rules"] and "US English" in sent["rules"]
    assert writer.audited and writer.audited[0]["letter"] == draft["body"].strip()


def test_a_draft_that_mentions_her_visa_is_sent_back_then_replaced(service):
    job = add(service.w)
    bad = good_draft(service, job)
    bad["body"] += "\n\nI am on F-1 OPT and will need H-1B sponsorship later."
    writer = StubWriter(dict(bad), dict(bad))
    letter = service.generate_cover_letter(job["id"], team=writer)
    assert letter["method"] == "template" and "set aside" in letter["note"]
    assert "immigration" in writer.payloads[1]["previous_attempt_problem"]
    assert not cover_letters.IMMIGRATION.search(letter["content"])


@pytest.mark.parametrize("sentence", [
    "I hold a green card.", "I am a US citizen.", "I am on STEM OPT.", "My H1B transfer is quick.",
    "I will need visa sponsorship.", "My employer can use E-Verify.",
])
def test_us_immigration_words_never_reach_a_letter(sentence):
    assert cover_letters.IMMIGRATION.search(sentence)


def test_ordinary_words_are_not_mistaken_for_immigration():
    for sentence in ("I optimized SQL queries.", "I wrote options pricing code.", "Citizens Bank was a client."):
        assert not cover_letters.IMMIGRATION.search(sentence.replace("Citizens Bank", "Example Bank")), sentence


def test_dates_are_written_the_us_way():
    assert cover_letters.long_date("2026-10-09") == "October 9, 2026"


def test_the_letter_downloads_as_word_and_markdown(service):
    job = add(service.w)
    letter = service.generate_cover_letter(job["id"])
    md, md_name = cover_letters.download(service, job["id"], "md")
    docx, docx_name = cover_letters.download(service, job["id"], "docx")
    assert md.is_file() and md_name.endswith("-cover-letter-v1.md")
    assert docx.is_file() and docx_name.endswith(".docx")
    text = docx_export.document_text(docx.read_bytes())
    assert NAME in text and "Sincerely," in text
    assert letter["content"].splitlines()[0] == NAME


def test_the_word_resume_is_the_same_checked_draft_on_a_us_letter_page(service):
    job = add(service.w)
    studio = ResumeStudio(service)
    draft = studio.open(job["id"])
    data = docx_export.cv_document(draft["source"], title="Resume")
    document = Document(io.BytesIO(data))
    section = document.sections[0]
    assert abs(section.page_width.mm - 215.9) < 0.5 and abs(section.page_height.mm - 279.4) < 0.5
    text = docx_export.document_text(data)
    assert NAME in text
    for heading in ("Education", "Professional Experience", "Projects"):
        assert heading in text
    # Nothing the PDF does not say: no LaTeX commands or comments leak into the copy.
    assert "\\" not in text and "% EVIDENCE" not in text
