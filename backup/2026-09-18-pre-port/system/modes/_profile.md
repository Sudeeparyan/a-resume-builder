# Personal overrides — Annie Prasanna Manoharan

<!-- ============================================================
     THIS FILE IS YOURS. It is never auto-updated and always wins
     over system/modes/_shared.md. Put anything specific to this person's
     search here: scoring tweaks, no-go companies, tone, policy.
     ============================================================ -->

## Scoring overrides
Adjust the weights from `system/modes/_shared.md` if this search has a different shape.

| Dimension | Default | This person | Why |
|-----------|---------|-------------|-----|
| Skill match | 35% | 40% | Raised — eligibility is no longer a weight (see below), and her real range spans four tracks, so skill match is doing the most work; see `system/profile/positioning.md` |
| Competition | 25% | 30% | Raised — she is an entry-level applicant in crowded US markets, so applicant volume per opening predicts a callback better than anything else |
| Eligibility | 20% | **0% — now a GATE, not a weight** | Sponsorship is decided *before* scoring by `system/scripts/sponsor_check.py`. A role either passes the gate or is excluded entirely; there is nothing left to score. |
| Company profile | 10% | 15% | Raised — absorbs part of the freed eligibility weight; cap-exempt status and company size matter a lot for her |
| Recency | 10% | 15% | Raised — a posting under 7 days old is worth far more than a 3-week-old one at entry level |

**After scoring, order by sponsorship tier first, score second: S → A → B → C.**
A tier-C role scoring 85 still ranks below a tier-S role scoring 75, because the cap-exempt
employer can actually file for her without a lottery.

## Hard filters
Roles the hunter must never surface, whatever they score.

1. **Postings that explicitly refuse to sponsor.** Group 1 in `system/config/sponsorship.yml`.
2. **Postings requiring US citizenship, a security clearance, ITAR/EAR status, or permanent
   residency.** Group 2. Different reason — they cannot lawfully hire her — same action.
3. **Anything on the tracker exclusion list** (`track.py --exclusions`): same company + same role
   ever, or a company that rejected her within 180 days.
4. Senior / Staff / Principal / Lead / Manager / Director titles.
5. Roles requiring more than 4 years of experience.

**These are the only hard filters.** In particular:
- Absence of H-1B history is **never** a filter.
- "Must be authorized to work in the US" is **never** a filter — she is authorized, on OPT.

## No-go companies
| Company | Reason |
|---------|--------|
| None stated | `context/07-preferences.md` Q7 is unanswered. Staffing and consulting firms are a live question — many sponsor in volume, but the work differs a lot from a product company. Ask before assuming. |

The generated exclusion list lives in `system/data/applied-companies.md` — never hand-edit it.

## Tone and voice
How this person's materials should read. See `context/08-voice.md` for the full reasoning.
- Professional but plain — complete, structured sentences that explain *why* something mattered,
  not just what was done. Not casual, not stiff.
- Genuine, recurring language worth keeping: "ownership," "real-world impact,"
  "problem-solving," "adaptability."
- US English spelling (target market = United States) — this overrides the workspace's US
  default.
- Her career is a real multi-step pivot (electronics → embedded → test automation → AI/ML
  research → data engineering). Each resume should pick one coherent thread for that employer
  rather than narrating the whole journey on one page.

## Negotiation position
- Target: {{COMP_RANGE}} USD · Walk-away: {{COMP_MINIMUM}}
- Non-salary priorities: visa sponsorship is likely to matter as much as salary, given her
  confirmed status — but this needs her direct confirmation, not an assumption.
- Opening line when asked for expectations: her own stated answer in `HR.pdf` (Q20) — "I am open
  to discussing compensation based on the responsibilities of the role, the overall benefits, and
  the market range for the position." Fine for an early screening call; a real number is still
  needed to filter postings (see `context/07-preferences.md`).

## Standing instructions
Anything you want applied to every output for this person.
- Confirm her exact visa/OPT status with Annie before using work-authorization eligibility to
  filter or rank any real job search — right now it's "needs sponsorship" in general, not a
  specific timeline. See `context/QUESTIONS-FOR-YOU.md`.
- Never state the ~94% test-automation figure from `About me.pdf` as tied to the Medtronic project
  specifically until she confirms it.
