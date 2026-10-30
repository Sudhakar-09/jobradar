# Changelog

## Unreleased

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