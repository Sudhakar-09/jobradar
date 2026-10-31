# Project progress

## Current phase

Phase 1 — Profile & packs is implemented and validated. The engineering documentation step is
in progress (Steps 1–5 done; Step 6 drafted and awaiting review; Step 7 next). Phase 2 —
Discovery starts after Step 7. The active checkout is
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
- Follow-up requested 2026-10-30:
  - Verified `.github/copilot-instructions.md` and `AGENTS.md` both point to `CLAUDE.md`.
  - Changed active target packs to UAE and Java Backend and recorded the user decision.
  - Disabled dotenv loading for tests; `uv run pytest`, Ruff, and mypy pass without overrides.
  - Recorded why the local host Redis port is 6380 and made the engineering docs a gate before
    Phase 2.
  - `cf59d0a` — `chore: align target packs and isolate tests`

- Engineering documentation, Steps 1–5 (approved by the owner; committed 2026-10-30 as separate
  conventional commits — see `git log`):
  - `docs: PRD` — `docs/prd.md` v0.4 (product for everyone; India + UAE / Java backend is the first
    configuration; stories by phase; multi-market quality gates).
  - `docs: HLD and ADRs` — `docs/architecture.md` v0.3 and ADR-0001 … ADR-0024.
  - `docs: LLD` — `docs/lld/` (database incl. per-phase migration plan, state machine, 16 module
    designs, canonical identifiers, traceability).
  - `docs: API contract` — `docs/api.md`, `docs/openapi.yaml` (hand-maintained), archived generator.
  - `chore: coding standards and tooling` — `docs/coding-standards.md`, ruff/mypy strict/
    import-linter/pre-commit, CI (quality, tests with coverage gates, contract, security with
    pinned actions, PR title), Dependabot, PR template; existing code conformed (Celery app moved
    to `jobradar.core.queue`).
  - `build: use the official pgvector PostgreSQL 16 image` and `chore(packs): add mid persona pack`.
  - Local, git-ignored `config/profile.yaml` sets persona and seniority `mid` for the owner.

## In progress

- Step 6 — UX and design system: owner chose Direction A "Calm Compass" with Direction B's
  celebration for interviews and offers (ADR-0025). `docs/design-system.md` (brand, voice,
  colour tokens with measured contrast, type, layout, motion, tokens build, components, icons,
  illustrations, accessibility, RTL, Storybook process) and `docs/ux.md` (principles, IA, global
  patterns, 8 journeys, 13 screens, digest channels) written and pushed; awaiting owner review.

## Next steps

- Step 6: owner review of `docs/design-system.md` and `docs/ux.md` (open UX questions in ux.md §8).
- Step 7: update `CLAUDE.md` (workflow per phase, revised phases 0–11, stack and layout changes,
  scratch-folder rule, commit and push after every step), remove the documentation gate below,
  commit and push.
- Phase 2 — Discovery (after Step 7), starting with the Phase 1 follow-ups: extend the
  `MarketPack`/`RolePack`/`PersonaPack` schemas (US-1.2 AC2/AC3), add Naukrigulf and channel
  access modes to the UAE pack, then connectors, alert ingestion, company catalogue, source
  policies, golden datasets and conformance v1 (US-2.1 … US-2.9).
- Replace the plain-text resume parser placeholder with LLM-based PDF and DOCX parsing after the
  LLM wrapper exists (Phase 3/4, US-1.4); add `pypdf` and `python-docx` at that time.

## Open questions/decisions waiting on me

- Step 6: review `docs/design-system.md` and `docs/ux.md`, including the open UX questions in
  `docs/ux.md` §8.

## Known issues

- Phase 0 standards review marks environment separation, expanded health/recovery, queue
  reliability, telemetry propagation, CI security/coverage, integration testing, and operational
  security as partial or deferred in `PRODUCT_STANDARDS.md`.
- This checkout's ignored `.env` sets the host ports to PostgreSQL 5433 and Redis 6380 because
  unrelated containers already bind host ports 5432 and 6379. Docker maps these host ports to
  the containers' normal ports (5432 and 6379); do not stop the unrelated containers. Tests now
  disable `.env` loading so their results do not depend on these local overrides.
- The previous OneDrive checkout remains on disk and must not be used for future work.
- The engineering documentation (Steps 6–7 remaining) is a release gate before Phase 2.
- CI: the first run on the new setup failed (ruff formatted Markdown code blocks; a multi-hook
  pre-commit call). Fixed in `d31725a`, whose run passed. Dependabot may open update PRs.
- The plain-text resume parser is a placeholder until the LLM wrapper and PDF/DOCX parsing are
  available.
