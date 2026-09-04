# Mode: evaluate — score one opportunity before spending effort on it

Input: a JD (pasted or URL). Output: blocks A–F plus a priority score and a go/no-go.
Read `system/modes/_shared.md` then `system/modes/_profile.md` first.

## Block A — Role summary
Company, role, team, location, work mode, seniority, posted date, applicant count if visible,
salary if stated, apply route (direct / ATS / agency).

## Block B — Requirement match
| JD requirement | Evidence from `system/profile/master-profile.md` | Level | Verdict |
|----------------|-------------------------------------------|-------|---------|
Verdict is `strong` / `partial` / `gap`. Every strong row must name a real project or role.
Score = strong count + 0.5 × partial count, over total must-haves.

## Block C — Competition read
Applicant count, how common the required combination is, company size, how long the posting has
been live, whether it is reposted, whether an agency is between you and the employer.

## Block D — Eligibility
Work authorisation, location and relocation, language, seniority band, any licence or clearance.
A hard fail here means score 0 regardless of skill match — say so plainly.

## Block E — Personalisation hooks
Two or three specific, checkable things about the company: a product, a recent launch, the stack in
their engineering blog, a team member's public work. These become the cover letter and the Projects
reframe. If research is unavailable, say so rather than inventing detail.

## Block F — Interview exposure
The three questions this JD most likely leads to, and which stories from
`system/profile/interview-stories.md` answer them. Name any question with no story behind it.

## Verdict
`Priority score: NN/100` using the weights in `system/modes/_shared.md`, then:
- **Apply** — with the track and base to use
- **Apply if** — the one condition that would make it worth it
- **Skip** — the single clearest reason, recorded in the tracker
