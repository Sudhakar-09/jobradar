# Project progress

## Current phase

Phase 1 — Profile & packs is implemented and validated. Phase 2 — Discovery is next. The active
checkout is `C:\dev\jobradar`; do not continue work from the retained OneDrive copy.

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
  - Added India and United States market packs and a Software Engineer role pack.
  - Added `jobradar profile show` and a plain-text resume parser that reads only explicit labels.
  - Added tests for loaders, validation, pack loading, resume parsing, and the CLI.
  - Validation: all 22 tests pass, Ruff passes, mypy passes, and `jobradar profile show` prints
    validated JSON. The test run set `REDIS_PORT=6379` to isolate the pre-existing local `.env`
    override described below.

## In progress

- Phase 1 changes are complete; commit and push are pending.

## Next steps

- Start Phase 2 — Discovery:
 - Implement the connector base plus Greenhouse, Lever, Ashby, Adzuna, and Remotive.
 - Add the jobs table, deduplication, source-run tracking, fixture tests, and CLI discovery.

## Open questions/decisions waiting on me

- None.

## Known issues

- Phase 0 standards review marks environment separation, expanded health/recovery, queue
  reliability, telemetry propagation, CI security/coverage, integration testing, and operational
  security as partial or deferred in `PRODUCT_STANDARDS.md`.
- Other running containers occupy host ports 5432 and 6379; this checkout uses ignored local
  `.env` overrides on ports 5433 and 6380. Do not stop the unrelated containers.
- The previous OneDrive checkout remains on disk and must not be used for future work.
