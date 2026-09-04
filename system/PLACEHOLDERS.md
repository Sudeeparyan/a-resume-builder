# Placeholder reference

Every token below appears somewhere in the template. `system/scripts/init_profile.py --check` lists the
ones still unfilled. Tokens are always `{{UPPER_SNAKE_CASE}}` inside double braces.

## Identity
| Token | Meaning | Example |
|-------|---------|---------|
| `{{FULL_NAME}}` | Name as it appears on the resume header | Jane Q. Candidate |
| `{{EMAIL}}` | Contact email | jane@example.com |
| `{{PHONE}}` | Contact phone with country code | +1 (479) 301-1366 |
| `{{CITY}}` | City | Fayetteville |
| `{{COUNTRY}}` | Country | the United States |
| `{{POSTAL_LINE}}` | Optional second header line | Fayetteville, AR |
| `{{LINKEDIN_URL}}` | LinkedIn profile URL | https://linkedin.com/in/... |
| `{{GITHUB_URL}}` | GitHub/GitLab URL (omit if none) | https://github.com/... |
| `{{PORTFOLIO_URL}}` | Portfolio/site URL (omit if none) | https://... |

## Positioning
| Token | Meaning |
|-------|---------|
| `{{HEADLINE}}` | One-line positioning statement, ≤120 chars |
| `{{SUMMARY_PARAGRAPH}}` | 2–3 line resume summary, rewritten per JD |
| `{{YEARS_EXPERIENCE}}` | Honest professional years — omit entirely if none |
| `{{CURRENT_STATUS}}` | e.g. "MSc student", "employed at X", "seeking first role" |
| `{{WORK_AUTH}}` | Visa/work-authorisation status, or "Citizen — no sponsorship needed" |
| `{{TRACK_A_NAME}}` / `{{TRACK_B_NAME}}` | The two career lanes this person can credibly target |
| `{{HERO_METRIC_1}}`…`{{HERO_METRIC_5}}` | Signature quantified wins (leave blank if none exist) |

## Education
`{{DEGREE_1}}`, `{{INSTITUTION_1}}`, `{{EDU_LOCATION_1}}`, `{{EDU_DATES_1}}`, `{{EDU_DETAIL_1}}`
— repeat with `_2`, `_3`.

## Experience
`{{EMPLOYER_1}}`, `{{ROLE_1}}`, `{{EMP_LOCATION_1}}`, `{{EMP_DATES_1}}`, `{{EMP_BULLET_1_1}}`…
— repeat per employer. Delete unused blocks entirely rather than leaving empty tokens.

## Projects
`{{PROJECT_1_NAME}}`, `{{PROJECT_1_LINK}}`, `{{PROJECT_1_DATES}}`, `{{PROJECT_1_BULLET_1}}`…

## Skills
`{{SKILL_CATEGORY_1}}` / `{{SKILL_LIST_1}}` — repeat per category, ordered so the JD's top tools
appear first.

## Targets & region
| Token | Meaning |
|-------|---------|
| `{{REGION}}` | Country or market being targeted, e.g. the United States |
| `{{REGION_SLUG}}` | Lowercase folder name, e.g. `united-states` |
| `{{TARGET_ROLE_1}}`… | Job titles to search for |
| `{{COMP_RANGE}}` / `{{CURRENCY}}` | Target compensation band |

## Company-specific (filled per application)
`{{COMPANY}}`, `{{ROLE_TITLE}}`, `{{HIRING_MANAGER}}`, `{{APPLICATION_NUMBER}}`, `{{DATE}}`
