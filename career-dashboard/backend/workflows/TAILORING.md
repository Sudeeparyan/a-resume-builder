# From saved posting to reviewed resume

Read `AGENTS.md`, `data/config/profile.yml`, `data/context/evidence.yml` and `data/context/QUESTIONS-FOR-YOU.md` first.

1. Verify the specific posting in a browser and save the complete JD, original URL and access date. A careers homepage or a logged-out error page is not a verified vacancy.
2. Run the gates: the sponsorship gate (an explicit refusal, or a citizenship/clearance/ITAR/EAR/permanent-residency requirement, excludes the posting and logs the sentence) and the never-re-apply check. Then evaluate every essential requirement, seniority (entry level, ≤4 years) and the US location. Set `role_eligible` to true only after the decision is supported; record constraints in `evaluation.md`.
3. Research the employer from current primary sources (`backend/workflows/modes/deep.md`). Keep explicit statements separate from inference. Explain which real employer problem makes the signature project relevant; employer research never becomes candidate experience.
4. Prepare the draft through the dashboard (Resume Studio) or `backend/scripts/career.py prepare`. The signature project is the best-ranked project no other company owns; the supporting project is the next best. Tailor ordering and emphasis without strengthening any claim.
5. Complete `evidence-map.yml`. Each requirement needs an ID, priority, exact text, evidence IDs and `strong`, `partial` or `gap`. Supported coverage uses required weight 3, preferred weight 1, strong 1, partial 0.5, gap 0. Gaps go to `study-plan.md`, never onto the page. Keep the registry revision and the saved-JD hash correct.
6. Fit to one US Letter page (Resume Studio → Fit to one page: 11 → 10.5 → 10pt, then the documented cuts; never smaller type or margins). Run full validation and resolve every failure in the source or evidence map. Inspect the page image for clipping, layout and readable text.
7. Record the visual review with the validator only after seeing the latest page. Keep all nine artifacts together. A QA pass does not carry forward after the resume or registry changes.
8. Write the study plan (Resume Studio → Write study plan) and say the wall out loud: nothing in it goes on the resume until learned and recorded.
9. Hand Annie the files and one plain next step. Submitting and any outreach need her explicit go-ahead.

The dashboard stores jobs in `data/career.db` and shows every PDF as a draft until its source, PDF, evidence revision and review status match. Its actions never submit applications.
