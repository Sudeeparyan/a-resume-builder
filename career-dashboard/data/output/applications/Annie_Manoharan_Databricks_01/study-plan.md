# Study plan for Databricks - Software Engineer, Web Products

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill (JD wording) | Bucket | Why the JD wants it |
|---|---|---|
| Databricks platform familiarity | Have | Company product surface; she holds it as a registered skill |
| HTML, CSS, CI/CD, Git, TDD, design patterns, Agile | Have | 'Strong fundamentals across the web stack... build systems, and deployment pipelines' |
| LLM/agent tooling (LangChain, RAG, prompt engineering) | Have | 'AI native tools and an AI native engineering lifecycle are embedded in how the team builds' |
| TypeScript + component architecture + design systems | Learnable (Tier 1-2) | 'Implement components and page systems using a shared design system' |
| Rendering strategies (SSR/SSG/ISR) + build systems | Learnable (Tier 1) | 'Strong fundamentals across... rendering strategies, build systems' |
| Headless CMS (Contentful, Drupal) | Learnable (Tier 2) | 'Experience building on or integrating with content management systems like Drupal, Contentful' |
| Edge delivery / CDN deployment | Learnable (Tier 2) | 'Familiarity with headless CMS architectures, edge delivery... is a strong plus' |
| AI-native SDLC practice (agents in codegen/testing/deploy) | Learnable (Tier 1-2) | 'Operate in an AI native SDLC where agents assist across code generation, testing, and deployment' |
| AI-driven search / structured discovery (GEO) | Learnable (Tier 2) | 'Optimized for... AI driven search and discovery systems' |
| React / Next.js (modern frontend framework) | Never-claim (learnable) | 'Modern frontend frameworks is a strong plus'; React is on the never-claim list - learn it, never claim it yet |
| 4+ years shipping production web systems | Structural | Hard requirement; cannot be built in 6 weeks |
| Export-controlled access eligibility | Structural | Compliance clause; answer factually if asked |

(The 'Excel' and compensation items flagged as gaps are noise, not skills.)

## Tier 1 - before the screening call (week 1-2)

1. **TypeScript fundamentals** - types, generics, module patterns, why teams prefer it for shared design systems. Resource: the official TypeScript Handbook (typescriptlang.org/docs/handbook). Self-check: in 30 min, convert a small JS utility to typed TS and explain three compiler errors you fixed.
2. **Component architecture and design systems** - presentational vs container components, tokens, composition. Resource: Brad Frost's 'Atomic Design' (free online). Self-check: sketch databricks.com's nav/card/footer as a component tree from memory.
3. **Rendering strategies** - SSR vs SSG vs ISR vs client rendering, and when each wins for marketing pages and blogs. Resource: web.dev's rendering-on-the-web guide. Self-check: for five page types (blog, landing, docs, dashboard, event page), name the strategy and justify in one line each.
4. **Headless CMS vocabulary** - content models, entries, delivery vs preview APIs, Drupal vs Contentful positioning. Resource: Contentful's 'Headless CMS explained' docs. Self-check: explain to a rubber duck how a blog post travels from CMS entry to rendered page.
5. **AI-native SDLC fluency** - agent-assisted codegen, AI review, test generation; she has LLM foundations, now map them to a delivery pipeline narrative. Resource: GitHub Copilot docs on agent mode. Self-check: describe in 60 seconds how an agent fits at each stage: code, test, review, deploy.

## Tier 2 - before the technical round (week 2-5)

1. **Next.js depth (learn, not claim)** - App Router, server components, ISR, routing. Resource: the official Next.js Learn course. Artefact: a small repo with one SSG page and one ISR page, README explaining the choice.
2. **Headless CMS integration** - build a content model in Contentful's free tier, fetch via delivery API. Artefact: the same repo rendering CMS-driven blog entries, with a short walkthrough of the content model.
3. **Edge delivery** - deploy to Vercel/Cloudflare free tier; understand caching headers and CDN invalidation. Artefact: deployed URL plus a one-page note measuring cache hits/misses.
4. **AI-assisted build workflow** - run the whole project through an agent-assisted loop (Copilot/Cursor) and log what the agent got right and wrong. Artefact: a written walkthrough 'building with an agent: 10 prompts, 3 corrections' - this is exactly the team's operating model and a strong talking point.
5. **GEO / structured data** - schema.org markup, sitemaps, llms.txt, how AI crawlers consume pages. Artefact: the project emitting JSON-LD and a validated rich-result test screenshot.

## Build-now project (not built yet)

**'Conference microsite on a headless CMS'** - mirrors 'landing pages, hubs, and event properties'.
- Goal: a public microsite for a fictional data conference, CMS-driven, edge-deployed.
- Data: sessions, speakers, sponsors modeled as Contentful content types.
- Stack: Next.js + TypeScript, Contentful free tier, Vercel edge deployment, GitHub Actions CI (she has CI/CD).
- Build: agent-assisted throughout; keep the prompt log.
- Evaluation: Lighthouse >90, ISR revalidation working, JSON-LD validated.
- Deliverable: public repo + live URL + 1-page architecture note.
- Hours: ~25-30 over three weeks.

## Honest answers for the structural gaps

- *Years of production web:* 'My production shipping experience is in data and ML systems, not four years of web product work. I'm strong on the delivery fundamentals - CI/CD, testing, code review - and I've spent the last month building on the exact stack this team runs. I'd grow fastest under senior direction, which is what this role describes.'
- *Framework depth:* 'React/Next.js is new for me - here's the repo I built to learn it. I'd rather show you working code than inflate a bullet.'
- *Export control:* 'I understand some duties may involve export-controlled technology; I'm happy to discuss my work authorization status openly.'

## When this may go on the resume

Only after a skill is learned AND written into data/context/, then re-registered - nothing in this plan is resume-ready today.
