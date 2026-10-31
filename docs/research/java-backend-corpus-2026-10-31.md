# Java backend postings in the JobRadar corpus (2026-10-31)

Evidence for `packs/verification/java_backend.yaml`. Aggregate counts only; no posting text is
reproduced. Corpus after `jobradar discover` on 2026-10-31: 5,629 new jobs from the 36 UAE
catalogue boards plus alert emails and Remotive (≈ 5,700 jobs). Most catalogue employers are
global, so the corpus is dominated by US, Singapore and UK postings; India and Germany come
mainly from alert emails (no description text). Queries: `scripts/archive/` not needed —
the SQL is reproduced below.

## Java postings by country

Postings whose title mentions Java, and postings whose description mentions Java (≥ 300
characters of text):

| Country | Java in title | Java in description |
|---|---|---|
| US | 3 | 173 |
| unknown location | 20 | 133 |
| SG | 9 | 103 |
| GB | 4 | 45 |
| IN | 18 | 34 |
| CA | 4 | 24 |
| DE | 3 | 10 |
| AE | — | 2 (title or description) |

**UAE:** only 2 Java postings located in the UAE across the 36 UAE-hiring catalogue companies:
those employers hire few Java backend engineers in the UAE; UAE Java roles reach JobRadar mainly
through alert emails.

## Titles (postings mentioning Java with an engineering title)

| Title pattern | Count |
|---|---|
| software engineer | 293 |
| backend engineer | 28 |
| java engineer | 19 |
| full stack | 15 |
| software developer | 13 |
| java developer | 7 |
| backend developer | 4 |
| software development engineer (SDE) | 3 |
| java backend engineer | 3 |
| java backend developer | 3 |
| platform engineer | 2 |

## Skills (498 Java backend-type postings with description text; share mentioning)

| Skill | Share |
|---|---|
| testing (tests, JUnit, TDD) | 41 % |
| distributed systems | 39 % |
| cloud (AWS, GCP, Azure) | 38 % |
| REST / APIs | 38 % |
| Docker / Kubernetes | 36 % |
| CI/CD | 27 % |
| SQL / relational databases | 27 % |
| Kafka | 18 % |
| system design | 17 % |
| microservices | 16 % |
| Kotlin | 15 % |
| Spring | 14 % |
| Maven / Gradle | 9 % |

## Seniority and process signals (524 postings)

| Signal | Count |
|---|---|
| title: senior | 197 |
| title: staff / principal | 120 |
| title: level II / III | 23 |
| title: lead | 15 |
| title: junior / graduate | 1 |
| text: "N+ years" | 303 |
| text: 3–5 years | 167 |
| text: hiring manager | 12 |
| text: coding / technical assessment | 1 |
| text: system design interview | 0 |

Postings rarely describe the interview process, so stages and assessment types cannot be
verified from postings.

## Limits

The corpus reflects the UAE catalogue's (mostly global) employers, not the Indian or German
Java market; it will be re-run once the India and Germany company lists are approved.

## SQL

```sql
-- Java backend-type postings (base set for titles, skills and seniority)
with j as (
  select lower(title) t, lower(coalesce(description, '')) d from jobs
  where (title ~* '\mjava\M' or description ~* '\mjava\M')
    and title ~* '(backend|back-end|software|engineer|developer|sde)'
)
select count(*) filter (where t ~ 'software engineer') as software_engineer,
       count(*) filter (where d ~ '\mspring') as spring,
       count(*) filter (where t ~ '\msenior\M|\msr\.?\M') as senior
from j;
-- Skill shares used only postings with length(description) > 300; each skill is a
-- case-insensitive regex, e.g. testing: '\mtest(s|ing)?\M|junit|tdd',
-- sql: '\msql\M|postgres|mysql|oracle', cloud: '\maws\M|\mgcp\M|azure|google cloud'.
```
