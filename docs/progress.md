# Project progress

## Current phase

Phase 0 — Scaffold is implemented. Phase 1 — Profile & packs is the next phase. The active
checkout is `C:\dev\jobradar`; do not continue work from the retained OneDrive copy.

## Done (with commit hashes)

- Phase 0 scaffold: Python project, quality tooling, settings, structured logging, PostgreSQL and
  Redis Compose services, Alembic baseline, health/readiness endpoints, CI checks, and Windows
  development tasks.
  - `1765857143ed297833ed7db58765161b51da464c` — `Phase 0: scaffold`
  - `6dd87894c9baaa862ec25d630a428eaef7447b39` — `chore: phase 0 follow-ups`
- Relocated the active checkout to `C:\dev\jobradar`; the original OneDrive checkout was retained.
- Recreated the environment with `uv sync --link-mode=copy`; all 10 tests pass, including the
  installed-package metadata test.
- Started PostgreSQL and Redis, applied Alembic migrations, and verified `/health` and `/ready`
  return `ok`.

## In progress

- Complete GitHub device authorization, then configure Git credential management and push the
  prepared commits to `origin`.

## Next steps

- Start Phase 1 — Profile & packs:
  - Add profile and answer-bank loaders.
  - Add validated pack schemas and India plus one target-market and one role pack.
  - Add resume parsing into a structured profile.
  - Meet the phase acceptance criterion: `jobradar profile show` prints the validated profile.

## Open questions/decisions waiting on me

- The target market and role pack for Phase 1 have not yet been selected or recorded.

## Known issues

- Phase 0 standards review marks environment separation, expanded health/recovery, queue
  reliability, telemetry propagation, CI security/coverage, integration testing, and operational
  security as partial or deferred in `PRODUCT_STANDARDS.md`.
- Other running containers occupy host ports 5432 and 6379; this checkout uses ignored local
  `.env` overrides on ports 5433 and 6380. Do not stop the unrelated containers.
- The previous OneDrive checkout remains on disk and must not be used for future work.
