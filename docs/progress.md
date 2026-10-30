# Project progress

## Current phase

Phase 1 — Profile & packs is implemented and validated. Phase 2 — Discovery has not started; the
engineering documentation listed below must be completed first. The active checkout is
`C:\dev\jobradar`; do not continue work from the retained OneDrive copy.

## Done (with commit hashes)

- Phase 0 scaffold: Python project, quality tooling, settings, structured logging, PostgreSQL and
  Redis Compose services, Alembic baseline, health/readiness endpoints, CI checks, and Windows
  development tasks.
  - `1765857143ed297833ed7db58765161b51da464c` — `Phase 0: scaffold`
  - `6dd87894c9baaa862ec25d630a428eaef7447b39` — `chore: phase 0 follow-ups`
- Durable project memory and session instructions, including the C-drive location decision.
  - `648e70fe2b84e00c0e794e8f622fbc0b34ed73f4` — `docs: add progress and decision logs`
  - `9cca1aa` — `docs: add universal Copilot session instructions`
- Relocated the active checkout to `C:\dev\jobradar`; the original OneDrive checkout was retained.
- Recreated the environment with `uv sync --link-mode=copy`; all 10 tests pass, including the
  installed-package metadata test.
- Started PostgreSQL and Redis, applied Alembic migrations, and verified `/health` and `/ready`
  return `ok`.
- Authenticated GitHub CLI with the required `workflow` scope and pushed `main` to `origin`.
- Phase 1 — Profile & packs:
  - Added Pydantic schemas and YAML loaders for profiles, answer banks, market packs, role packs,
    and persona packs.
  - Added India and UAE market packs and a Java Backend role pack, based on the user's target.
  - Added `jobradar profile show` and a plain-text resume parser that reads only explicit labels.
  - Added tests for loaders, validation, pack loading, resume parsing, and the CLI.
  - Tests disable local dotenv loading. Validation: `uv run pytest` passes all 23 tests without
    environment overrides; Ruff and mypy also pass.
  - `9d028e8` — `Phase 1: profile and packs`

## In progress

- None. `main` tracks `origin/main`; the current project changes have been pushed.

## Next steps

- Before Phase 2 — Discovery:
  - Complete the skipped engineering documentation: PRD, HLD, LLD, API contract, coding standards,
    and UX. This is a hard prerequisite; do not begin Phase 2 until these documents are complete.
  - Replace the plain-text resume parser placeholder with LLM-based PDF and DOCX parsing after the
    LLM wrapper exists; add `pypdf` and `python-docx` at that time.
- After the prerequisite work, start Phase 2 — Discovery:
 - Implement the connector base plus Greenhouse, Lever, Ashby, Adzuna, and Remotive.
 - Add the jobs table, deduplication, source-run tracking, fixture tests, and CLI discovery.

## Open questions/decisions waiting on me

- None.

## Known issues

- Phase 0 standards review marks environment separation, expanded health/recovery, queue
  reliability, telemetry propagation, CI security/coverage, integration testing, and operational
  security as partial or deferred in `PRODUCT_STANDARDS.md`.
- This checkout's ignored `.env` sets the host ports to PostgreSQL 5433 and Redis 6380 because
  unrelated containers already bind host ports 5432 and 6379. Docker maps these host ports to
  the containers' normal ports (5432 and 6379); do not stop the unrelated containers. Tests now
  disable `.env` loading so their results do not depend on these local overrides.
- The previous OneDrive checkout remains on disk and must not be used for future work.
- The engineering documentation listed under Next steps is a release gate before Phase 2.
- The plain-text resume parser is a placeholder until the LLM wrapper and PDF/DOCX parsing are
  available.
