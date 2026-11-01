# Changelog

## Unreleased

### Phase 2 — Discovery (complete except real alert samples, 2026-11-01)

- ATS connectors (Greenhouse, Lever, Ashby, Workable, SmartRecruiters), Remotive and Adzuna
  (disabled: paid plan), all through `PoliteClient` (source policies, SSRF guard, rate limits,
  retries, no URL logging); `jobradar discover` with deduplicated ingest and connector health.
- Job-alert ingestion from Gmail (read-only, consent, encrypted token, bodies never stored) with
  config-driven readers for LinkedIn, Naukri, Naukrigulf, Bayt, GulfTalent, Instahyre and
  Foundit; the LinkedIn reader fixed against a real alert; `jobradar alerts reprocess`.
- Company catalogue of 134 verified companies (UAE 38, India 51, Germany 63), `companies verify`,
  `probe` and alert-based `suggestions`; follow lists for employers on unreadable systems.
- Germany market pack; EU Blue Card thresholds as dated data; language requirement detection;
  excluded-industries preference; seniority signals and conditional title aliases.
- Pack verification records against official sources, conformance suite v1, golden datasets for
  India, UAE and Germany, and the audited, conformance-gated flag service.
- Fixed a rate-limiter spin caused by float rounding; lowered the Workable request budget.

### Phase 1 — Profile and packs

- Added validated profile and answer-bank YAML loaders, market/role/persona pack schemas, India and
  UAE market packs, and a Java Backend role pack.
- Added the `jobradar profile show` CLI and a conservative plain-text resume parser.
- Disabled local `.env` loading in tests and documented engineering-documentation and resume-parser
  prerequisites before Phase 2.

## 0.1.0 - 2026-10-30

- Scaffolded the Python 3.12 project, quality tools, settings, and JSON logging.
- Added PostgreSQL 16 and Redis Compose services, Alembic baseline, and `/health` plus `/ready` checks.
- Added named Celery queues, request correlation IDs, restart policies, and GitHub Actions quality checks.
- Moved product standards to `docs/PRODUCT_STANDARDS.md` and documented the Phase 0 standards review.
- Enabled installed src-layout packaging and added Windows PowerShell development tasks.