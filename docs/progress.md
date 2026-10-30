# Project progress

## Current phase

Phase 0 — Scaffold is implemented. Phase 1 — Profile & packs is the next phase.

## Done (with commit hashes)

- Phase 0 scaffold: Python project, quality tooling, settings, structured logging, PostgreSQL and
  Redis Compose services, Alembic baseline, health/readiness endpoints, CI checks, and Windows
  development tasks.
  - `1765857143ed297833ed7db58765161b51da464c` — `Phase 0: scaffold`
  - `6dd87894c9baaa862ec25d630a428eaef7447b39` — `chore: phase 0 follow-ups`

## In progress

- None recorded. The latest commit is Phase 0 follow-up work.

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
- The current local virtual environment has incomplete `jobradar` package metadata: `uv run pytest`
  failed while replacing its installed metadata, and the direct test run passed 9 tests but failed
  `test_jobradar_package_is_installed_and_importable`.
- The intended private GitHub repository is configured as `origin`, but this environment has no
  GitHub CLI authentication and Git cannot prompt for credentials. The latest commit is local and
  still needs an authenticated push.
