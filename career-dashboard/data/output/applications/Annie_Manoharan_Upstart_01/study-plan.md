# Study plan for Upstart - Software Engineer, Distribution Platform

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Python / Java ('Strong proficiency in one or more programming languages') | Have | Core language bar |
| Scalable APIs & microservices on cloud ('Experience building scalable APIs and microservices in a cloud-based environment (e.g., AWS)') | Have | Team builds serving systems |
| 3rd-party integrations / large data ('integrate with 3rd parties and/or ingest, store, expose large amounts of data') | Have | Partner integrations, ads data |
| SQL / data warehouses ('Experience with SQL, data warehouses') | Have | Analytics collaboration |
| Bachelor's degree + 3 years experience | Structural | Minimum qualification; degree held, years are the gap |
| Ruby on Rails and/or Kotlin ('Professional experience with Ruby on Rails and/or Kotlin') | Missing, learnable | Their actual stack |
| React / TypeScript / front end ('Experience or interest in working with React, typescript, or front end technologies') | Never-claim (learnable now) | Occasional UI work on internal tools |
| Google Ads / Meta Ads ('Professional experience with digital advertising platforms') | Missing, learnable (knowledge); 'professional' part is structural | Highest-value channel is digital ads |
| Marketing tech / growth engineering ('Experience working with marketing technology or growth engineering') | Missing, learnable | Domain vocabulary for screening |
| Leading projects ('leading small to medium sized projects over multiple months') | Have | Multi-month project leadership in her history |

## Tier 1 - before the screening call (week 1-2)

1. **Marketing-tech vocabulary**: attribution, CAC/ROAS, conversion funnel, A/B testing, channel mix (digital ads, direct mail, partner integrations — the JD's own list). Resource: HubSpot Academy's free Digital Marketing course. Self-check: explain in 2 minutes how Upstart would measure a direct-mail campaign's lift.
2. **Ruby fundamentals**: syntax, blocks, gems, irb fluency. Resource: The Odin Project's Ruby course (free). Self-check: write a small CLI script parsing a CSV without looking up syntax.
3. **Google Ads platform basics**: campaigns, ad groups, bidding, the API's shape. Resource: Google Skillshop's free Google Ads courses. Self-check: whiteboard how you'd sync audience segments to Google Ads nightly.
4. **Rails mental model**: MVC, routing, ActiveRecord, migrations. Resource: official Rails Guides (guides.rubyonrails.org). Self-check: sketch the request lifecycle for 'GET /campaigns/:id' from memory.
5. **Upstart domain prep**: lending marketplace, AI underwriting, why distribution efficiency matters to unit economics. Resource: Upstart's engineering blog (upstart.com/engineering). Self-check: give a 90-second answer to 'why this team?' citing the JD's 'right users with the right content at the right time'.

## Tier 2 - before the technical round (week 2-5)

1. **Rails API depth**: build a CRUD JSON API with PostgreSQL, background job, and tests. Artefact: public GitHub repo with README and request examples.
2. **React + TypeScript basics** (never-claim until re-registered): components, hooks, typed props, fetching from the Rails API. Artefact: a small typed frontend repo consuming that API.
3. **Third-party integration patterns**: OAuth, webhooks, rate limits, retry with backoff, idempotency — directly relevant to 'integrate with 3rd parties'. Artefact: a repo that ingests a public API (e.g., ad-report-style CSV/JSON) into Postgres with retries and a written design note.
4. **Experimentation analytics**: A/B test design, significance, reading marketing data with SQL. Artefact: a Jupyter notebook analyzing a public marketing dataset with SQL + Pandas, ending in a go/no-go recommendation.
5. **Content-serving system design**: low-latency decisioning, caching, feature flags, audience targeting at scale. Artefact: a written one-page design walkthrough of 'serve the right content to the right user' with trade-offs.

## Build-now project (only if the JD needs a project type she has none of)

She has no web/full-stack service project of this type, so: **AdServe-lite (not built yet)**.
- Goal: miniature marketing-content serving service, mirroring the team's problem.
- Data: synthetic user/audience segments and creative metadata generated with Faker.
- Stack: Rails API + PostgreSQL + Redis-free in-memory cache; React/TypeScript admin UI; Docker Compose; deployed on AWS (EC2 or Lambda).
- Features: audience rules engine, per-user content decisioning endpoint, event logging to Postgres, simple A/B assignment.
- Evaluation: p95 latency < 50ms locally; unit tests for the rules engine; an experiment-results SQL query.
- Deliverable: GitHub repo, architecture diagram, 5-minute Loom walkthrough.
- Hours: ~40-50 over weeks 2-5.

## Honest answers for the structural gaps

- On '3 years of experience': "My experience is intensive and project-based rather than three years in industry — across my MS and multi-month team projects I've owned design, delivery, and collaboration end to end, and I'm confident ramping quickly on the parts that are new."
- On professional ad-platform experience: "I haven't run Google or Meta ads professionally yet — I've built the fundamentals through Skillshop and a demo campaign-serving service, so I understand the concepts and the API surface, and I'd be honest about where I'd need a teammate's review early on."

## When this may go on the resume

Only after a skill is genuinely learned AND written into data/context/, then re-registered — nothing in this plan may be claimed before that.
