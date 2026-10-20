"""Accuracy of the sponsorship gate on real-world wordings, in both directions.

Annie's rule: a posting that refuses sponsorship (or needs citizenship, a clearance or
US-person status) is never shown; everything else that fits her profile is. A missed
refusal wastes an application; a wrong exclusion hides a job she could get. Both kinds
of mistake were seen live before 2026-10-02 and are pinned here.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services.sponsorship import load_rules, screen  # noqa: E402

RULES = load_rules(str(ROOT / "data/config/sponsorship.yml"))

EXCLUDE = [
    # Refuses sponsorship.
    "We are unable to provide visa sponsorship for this role.",
    "Candidates must be able to work without current or future sponsorship.",
    "This position is not eligible for visa sponsorship.",
    "We will not sponsor visas now or in the future.",
    "Must not require current or future sponsorship.",
    "Sponsorship is not available for this position.",
    "No clearance needed, but we cannot sponsor visas.",
    "Candidates requiring sponsorship now or in the future will not be considered.",
    "Applicants who need sponsorship now or in the future are not eligible for this role.",
    "If you will require sponsorship now or in the future, you are not eligible for this position.",
    "Sponsorship now or in the future is not available for this role.",
    "We are not currently sponsoring visas.",
    "The company does not sponsor H-1B visas.",
    "We do not sponsor.",
    "Must be legally authorized to work in the US without employer sponsorship.",
    "Applicants must be able to work in the US without requiring visa sponsorship.",
    "This role is not eligible for immigration sponsorship.",
    "We are unable to sponsor or take over sponsorship of an employment visa at this time.",
    "We cannot provide H-1B sponsorship.",
    "Visa sponsorship will not be provided.",
    "We are not able to offer visa sponsorship for this position.",
    "Employer will not sponsor applicants for work visas.",
    "This position does not offer relocation or visa sponsorship.",
    # Cannot lawfully hire her at all.
    "This position requires U.S. citizenship.",
    "Open only to U.S. citizens.",
    "Applicants must be US citizens or permanent residents.",
    "Active Secret clearance required.",
    "Must be a U.S. citizen due to government contract requirements.",
    "U.S. citizenship is required.",
    "This position requires an active TS/SCI clearance.",
    "Must be a U.S. Person as defined by ITAR.",
    "Applicants must be eligible to obtain a security clearance.",
    "Green card holders and US citizens only.",
    # Seen on live boards on 2026-10-02.
    "Active Secret clearance required, experience with AWS a plus.",
    "- Active US Security clearance or eligibility and willingness to obtain a US Security clearance.",
    "Software Engineer - Reliability (US Citizen)",
    "Future sponsorship for work authorization is not available.",
    "We will not sponsor individuals for employment visas, now or in the future, for this job opening.",
]

KEEP = [
    # Absence notes written by research (both hid real entry-level postings before 2026-10-02).
    "No visa sponsorship or work-authorization sentence appears in the JD.",
    "The posting contains no statement about visa sponsorship, work authorization, citizenship, clearance or ITAR/EAR status.",
    "No sponsorship or citizenship language was found in the posting.",
    "There is no mention of visa sponsorship or security clearance.",
    "The JD does not mention sponsorship, citizenship or clearance.",
    "The posting is silent on sponsorship and clearance.",
    # The application form's question asks; it does not refuse.
    "Will you now or in the future require sponsorship for employment visa status?",
    "Do you require sponsorship to work in the US?",
    # Work authorization she already has.
    "Must be authorized to work in the United States.",
    "Must be authorized to work in the U.S.",
    "Eligible to work in the United States.",
    "Proof of eligibility to work will be required upon hire.",
    "This role is open to all candidates authorized to work in the US, including those on OPT.",
    "We participate in E-Verify.",
    # Negations and innocent nouns.
    "This role does not require a security clearance or US citizenship.",
    "No security clearance required.",
    "We proudly sponsor local hackathons and community events.",
    "Our executive sponsor for this initiative is the CTO.",
    "Experience with secret management tools such as HashiCorp Vault.",
    # Contractor terms are not visa terms.
    "No C2C. W2 only.",
    "No C2C or third-party agencies.",
    # Says yes.
    "We sponsor H-1B visas for qualified candidates.",
    "Visa sponsorship is available for this role.",
    "Applicants requiring visa sponsorship are encouraged to apply.",
    # Seen on live boards on 2026-10-02: an export-licence clause (it hid all of Cloudflare)
    # and a clearance that is only preferred (six Palantir software roles).
    "Please note that any offer of employment may be conditioned on your authorization to receive software or "
    "technology controlled under these U.S. export laws without sponsorship for an export license.",
    "- Active US Security clearance, or eligibility and willingness to obtain a US Security clearance is beneficial, but not necessary.",
    "An active Secret clearance is a plus.",
]


@pytest.mark.parametrize("text", EXCLUDE)
def test_refusals_and_cannot_hire_wordings_are_excluded(text):
    result = screen(text, RULES)
    assert result.verdict == "EXCLUDED", text
    assert result.sentence  # the exact wording is kept so a wrong call can be undone


@pytest.mark.parametrize("text", KEEP)
def test_everything_else_is_shown(text):
    assert screen(text, RULES).verdict == "KEEP", text


def test_the_quoted_sentence_is_the_posting_s_own_wording():
    text = "Great team.\nWe are unable to provide U.S. visa sponsorship for this role.\nApply today."
    assert screen(text, RULES).sentence == "We are unable to provide U.S. visa sponsorship for this role."


def test_positive_wording_ranks_as_explicit_sponsorship():
    assert screen("We sponsor H-1B visas for qualified candidates.", RULES).reason == "explicit_sponsorship"
