# Project progress

## Current phase

**Phase 2 — Discovery in progress** (sub-steps 2a–2h; design stage completed 2026-10-30). The active checkout is
`C:\dev\jobradar`; do not use the retained OneDrive copy.

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

- Step 6 — design system and UX: brand Direction A "Calm Compass" with Direction B's
  celebration for interviews and offers (ADR-0025); `docs/design-system.md`, `docs/ux.md`
  (`c966196`), then the owner's UX answers: swipe right = queue to apply with undo, possible
  matches only in Jobs, no remote images in emails, logos only via our caching proxy
  (`GET /companies/{company_id}/logo`, Phase 4; ADR-0022 amendment).
- Step 7 — `CLAUDE.md` rewritten for the final design: product for everyone, rules (incl.
  scratch-folder and commit-and-push-every-step rules), documentation map, stack, layout, data
  model, schedules per user time zone, phases 0–11 with acceptance criteria, per-story workflow.
  Documentation gate before Phase 2 lifted.

## In progress

Phase 2 — Discovery, worked in sub-steps 2a–2h (owner plan; STOP points at 2e, 2f, 2g, 2h).
- **2a done — pack schemas and source policies** (`feat(packs): …`, see `git log`):
  - `core/packs/` package: market (money, locales/RTL, CV norms with sensitive fields always off,
    visa routes, sources with access modes, credential recognition, provenance), role (taxonomy,
    ISCO-08, credentials per market, hiring patterns), persona (tailoring, follow-ups, top N,
    minimum fit) schemas; stale/unverified warnings for market and role packs.
  - `core/source_policies.py` + `config/source_policies.yaml`: 17 policies; unknown hosts one-tap.
  - India and UAE packs migrated; UAE adds LinkedIn, Naukrigulf, Bayt, GulfTalent (alert email +
    one-tap), monthly AED package, no income tax, en-AE + ar-AE. Java backend and mid packs
    upgraded.
  - Tests moved to `tests/unit/core/` (64 tests pass; coverage 95 % overall, 97 % critical).
  - Docs: new `docs/lld/packs.md`; ownership of `SourcePolicy`/`AccessMode` moved to `core`.
- **2b done — core building blocks** (`feat(core): …`):
  - `core.errors` (JobRadarError hierarchy incl. PolicyDeniedError, UnsafeUrlError),
    `core.scope` (UserScope, SystemScope), `core.clock` (SystemClock, FrozenClock),
    `core.ids` (UUIDv7), `core.aio` (selector loop on Windows for psycopg async).
  - `core.http.PoliteClient`: source-policy check per access mode, https only, non-public
    address block on every redirect hop, per-policy token bucket, connect/read/total timeouts,
    10 MB decoded-size cap, retries with jitter honouring Retry-After (capped), User-Agent with
    optional contact; logs host + path only. Residual DNS-rebinding risk noted for Phase 7 egress
    proxy.
  - `core.logging.redact_pii` processor (PII keys redacted, emails masked) in the JSON pipeline.
  - `core.db`: async engine with statement/lock timeouts, `user_session` (sets `app.user_id`),
    `system_session`.
  - New settings documented in `.env.example`. Dependencies declared: `httpx`, `tenacity`
    (stack-approved), `sqlalchemy[asyncio]` extra. 104 tests pass; coverage 95 % / 96 %.
- **2c done — Phase 2 tables, migration and row-level security** (`feat(db): …`):
  - Models for users (minimal), consents, companies, company_suggestions, source_runs,
    alert_inboxes, alert_messages, jobs (discovery columns only), job_sources, settings_flags,
    audit_log, dead_letters; naming convention from database.md §1.
  - Migration `0002_phase2`: citext, login-less roles `jobradar_app` / `jobradar_corpus` with
    grants, `app_current_user_id()`, forced RLS and policies per database.md §4. `core.db`
    switches every transaction into a role (`SET LOCAL ROLE`) because superusers bypass RLS.
  - Integration tests (testcontainers pgvector Postgres, works on Windows; fallback
    `JOBRADAR_TEST_DATABASE_URL` for compose): upgrade/downgrade/upgrade, model-vs-schema drift,
    forced RLS on every user-owned table, cross-user reads/writes blocked, corpus role denied user
    tables, flags/source runs/audit log policies, uniqueness rules. New CI job `integration`.
  - Local dev database migrated to `0002_phase2`. 117 tests pass (13 integration).
  - Dependency added: `testcontainers[postgres]` (dev, approved).
- **2d done — ATS connectors and `jobradar discover`** (`feat(connectors): …`):
  - Plug-ins for Greenhouse, Lever, Ashby, Workable, SmartRecruiters (entry points), checked at
    startup against source policies and `config/connectors.yaml` (URLs only in config).
  - Item-level validation: invalid items counted, wrong envelope = schema drift (`degraded`).
  - Health rules (US-2.6), run records in `source_runs`, 404 streak retires a board after 3 runs.
  - Normalizer ingest + dedupe (US-2.3): company/title normalization (legal suffixes, gender
    markers), location from source hints and `config/locations.yaml`, content hash for edits.
  - CLI: `jobradar companies sync`, `jobradar discover [--source] [--company]` (US-2.4); verified
    against the local dev database (catalogue still empty until 2g).
  - Live shape probe (one request per ATS, script deleted) found and fixed a PoliteClient bug that
    dropped query strings already in a URL.
  - 174 tests pass (18 integration: discover end to end, idempotent re-runs, edited postings,
    cross-board dedupe, 404 retirement, schema drift). Coverage 89 % / 93 % (unit job).
- **2e done (up to the Adzuna key) — aggregators** (`feat(connectors): Adzuna and Remotive …`):
  - Query connectors planned from packs (India + UAE × java_backend aliases); Adzuna covers India
    only (UAE skipped with a logged reason); predicted salaries never stored; Remotive one request
    per category, logos never stored.
  - Daily request budgets enforced from `source_runs`; skipped sources reported by `discover`.
  - Live check: `jobradar discover --source remotive` stored 12 real remote jobs, 0 invalid.
  - Security fix: httpx/httpcore no longer log full URLs (API keys in query strings).
  - 183 tests pass.
- Owner decision after 2e: Adzuna is paid (free plan = 25 test calls in total; £8/month for 500
  calls/day) and stays **disabled in Stage 1** (`enabled: false` in `config/connectors.yaml`,
  reported as skipped by `discover`). Stage 2 terms review: app registered for "Personal job
  search". India alert-email sources added (Instahyre, Foundit policies and India pack; PRD
  updated); their parsers come in 2f.
- **Pending:** one live Adzuna verification (single API call, response saved as an anonymized
  fixture). Waiting for `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` to be saved in `.env` (not on disk yet).
- **2f-1 done — alert parsers and ingestion (no Gmail yet)** (`feat(connectors): job-alert …`):
  - Parsers for LinkedIn, Naukrigulf, Bayt, GulfTalent (UAE) and Naukri, Instahyre, Foundit
    (India), one config-driven class; synthetic `.eml` fixtures per board (+ a no-jobs alert).
  - Ingestion: consent required, each message processed once, bodies never stored, per-user
    source run, degraded when a board's emails stop yielding jobs.
  - Minimal privacy (consents) and accounts (owner bootstrap) slices.
  - Dependencies added: `beautifulsoup4`, `google-auth-oauthlib` (approved).
  - 216 tests pass (26 integration). Coverage 85 % / 93 % (unit job).
- **2f-2 done — Gmail read-only connection** (`feat(connectors): Gmail …`):
  - Gmail client through `PoliteClient` (new `post_form`), endpoints in `config/inboxes.yaml`,
    query limited to alert senders and the last 3 days, raw messages decoded in memory.
  - Refresh token stored AES-GCM encrypted (`core/crypto.py`); revoked grants mark the inbox
    `reauth_required`; disconnect revokes at Google, deletes the token and ends consent.
  - CLI: `users bootstrap-owner`, `keys generate`, `inbox connect gmail|list|disconnect`,
    `alerts ingest`; `discover` includes the owner's inbox.
  - `cryptography` declared directly (already installed by google-auth) — **owner confirmation
    requested**. Google credential files are git-ignored as a safety net.
  - 242 tests pass (32 integration). Coverage 83 % / 93 % (unit job).
- Owner update (2026-10-31): `cryptography` approved; Adzuna live check skipped (no key in
  `.env`). The owner reported the Google setup and Gmail connection done, but this repository's
  `.env` has no `GOOGLE_OAUTH_CLIENT_FILE`/`TOKEN_ENCRYPTION_KEY` and the database has no owner
  account — to be re-done here before the first real alert ingest.
- **2g done — company catalogue** (`feat(connectors): company verify, probe and suggestions`):
  - `jobradar companies verify` (catalogue or `--file`; 24 h cache; records found/not found),
    `companies probe` (guessed slugs on the five ATSs, review output only),
    `companies suggestions list|probe|accept|reject` (employers from alerts, owner decides).
  - Alert ingestion now records unknown employers as per-user suggestions (merged by
    normalized name; ATS links give the board directly).
  - Live probe of 198 + 44 candidate employers (`config/company_candidates/`): **36 boards with
    UAE postings**, all re-verified with `companies verify --file` (36/36). Proposed list in
    `config/company_candidates/uae.proposed.yaml`; 7 boards have a single UAE posting.
  - Fixed a `PoliteClient` token-bucket spin (float rounding); regression test added.
  - 274 tests pass. Coverage 96 % overall.
- **Owner review of 2g (2026-10-31):** all 36 UAE companies approved (including the seven with a
  single UAE posting; verification re-checks them). Copied to `config/companies.yaml`, synced
  (36 new) and verified live (36/36). `companies verify` now reports cached boards separately.
  Work queue from the review: (2) excluded-industries preference, (3) India company list
  (≥ 50, for approval), (4) Workday/unknown systems stay one-tap via alerts. The owner redoes the
  Gmail setup in `C:\dev\jobradar\.env` (the earlier edit went to an old OneDrive copy).

- **Excluded industries (review item 2) done:** `config/industries.yaml` vocabulary, profile
  `excluded_industries` (empty for the owner), explicit `industries` tags on catalogue companies
  (10 UAE crypto companies tagged), unknown codes rejected. Enforced by the Phase 3 eligibility
  rule `excluded_industries` (LLD, database plan, OpenAPI and PRD US-3.2 updated).

- **Workday / unknown systems (review item 4) done:** confirmed one-tap via alert emails only;
  no code reads Workday boards; pinned by tests (source policies, connectors, probe, link
  detection).

- **Gmail connected (2026-10-31):** OAuth client file stored outside the repo
  (`%USERPROFILE%/.jobradar/`), `TOKEN_ENCRYPTION_KEY` and `GOOGLE_OAUTH_CLIENT_FILE` set in
  `C:\dev\jobradar\.env` (git-ignored), owner account bootstrapped, inbox connected by the owner
  (consent recorded). Docker Desktop had stopped; restarted with a WSL shutdown, data intact.
  First `jobradar alerts ingest`: **degraded** — 14 LinkedIn alert emails matched the sender but
  yielded 0 jobs, so the real LinkedIn layout differs from the synthetic fixture. Those messages
  are recorded as `unparsed`. Next: fix the LinkedIn parser against a real (anonymized) sample
  and re-process unparsed messages. Other boards' alerts had not arrived yet.

- **LinkedIn parser fixed (2026-10-31):** real LinkedIn alerts wrap each job card in one link;
  the parser now splits title from "Company · Location". Anonymized fixture from the owner's
  alert (original deleted; leak checks pass). New `jobradar alerts reprocess` re-read the 14
  unparsed emails: **76 jobs, 55 new, all 14 messages parsed**. 23 jobs are in India, none in the
  UAE (the owner's LinkedIn alert may cover India only). 285 tests pass, coverage 96 %.

- **Germany market added (owner, 2026-10-31):** `packs/markets/germany.yaml` (EUR annual gross,
  Blue Card / skilled worker / Opportunity Card, anabin, alert-email + one-tap boards LinkedIn,
  StepStone, XING, Indeed), StepStone and XING source policies, German cities, Adzuna `de`
  mapping, owner profile `target_markets` now india, uae, germany. CLAUDE.md, PRD §4.5 and
  rollout list, normalizer LLD (`germany_gross` model in Phase 3) updated. Germany company list
  and Germany conformance follow. 287 tests pass.

- **Language filter (owner, 2026-10-31):** `config/language_requirements.yaml` and
  `normalizer.language_signals` detect required / preferred languages and the posting language
  (English and German); owner profile `languages: [en]`; matching LLD: German-required postings
  ineligible, English postings rank higher.

- **EU Blue Card thresholds (owner, 2026-10-31):** dated table for 2025 and 2026 with sources
  and stale warnings (`core.dated_data`, `config/market_data/germany/eu_blue_card.yaml`); Germany
  pack route links to it; `visa_salary` warning rule specified for Phase 3.

- **Conformance v1 + golden datasets + rollout gate (2026-10-31):** `jobradar packs check`,
  golden samples for India, UAE and Germany (13 samples, expected output reviewed), `jobradar
  flags set|list` with the gate and audit. Status: UAE fails only `provenance`; India fails
  provenance, catalogue and Indeed parser; Germany fails provenance, catalogue and StepStone /
  XING / Indeed parsers; `java_backend` fails provenance. 343 tests pass, coverage 96 %.

- **UAE pack verified (2026-10-31):** per-value record (8 official, 15 secondary, 2 unverified
  for owner review), pack corrections applied; conformance now fails only on the 2 unverified
  values until the owner accepts or removes them.

- **India pack verified (2026-10-31):** per-value record (8 official, 14 secondary, 3 unverified
  for owner review); pack money notes, notice norm and CV photo scope corrected.

- **Germany pack verified (2026-10-31):** 32 values (26 official, 5 secondary, 1 unverified);
  skilled-worker and notice-period statements corrected; Blue Card thresholds now on official
  Bundesanzeiger notices incl. the IT-without-degree minimum. 345 tests pass.

- **Owner verification decisions applied (2026-10-31):** 6 items resolved and recorded
  (`owner_accepted_on`); India gaps in `known_gaps` and `docs/markets/india.md`. Conformance:
  **UAE PASS**; India and Germany wait for company lists and Indeed / StepStone / XING alert
  samples; `java_backend` role pack still to verify.

- **Role and persona verification (2026-10-31):** `jobradar discover` stored 5,629 new jobs
  from the UAE catalogue (3 Workable boards failed with 429 while the India probe ran); corpus
  analysis of 524 Java postings in `docs/research/`; records for `java_backend` and `mid` with
  ESCO / ISCO / secondary / corpus sources; editorial values await the owner. 346 tests pass.

- **Manual task for the owner (open):** follow the employers in `docs/research/uae-follow-list.md`
  on LinkedIn and create company job alerts, so their jobs (on systems JobRadar cannot read)
  arrive as LinkedIn alert emails. Tick each company in that file when done.

## Next steps

**Phase 2 — Discovery** (Stage 1). Work story by story using the workflow in `CLAUDE.md` §11:
1. ~~Pack schemas and UAE pack (US-1.2 AC2/AC3)~~ — done in 2a.
2. ~~Core building blocks~~ — done in 2b.
3. ~~Phase 2 tables, roles, RLS, integration tests~~ — done in 2c.
4. ~~Source policy registry (US-2.8)~~ — done in 2a (connectors re-export comes in 2d).
5. ~~ATS connectors (US-2.1)~~ — done in 2d. ~~Adzuna and Remotive (US-2.2)~~ — done in 2e
   (Adzuna live run waits for the owner's key).
6. ~~Dedupe and ingest (US-2.3) and `jobradar discover` (US-2.4)~~ — done in 2d.
7. Gmail job-alert ingestion and parsers for LinkedIn, Naukrigulf, Bayt, GulfTalent (US-2.5), with
   consent and body discard.
8. ~~Connector health and `degraded` detection (US-2.6)~~ — done in 2d (alerting arrives with ops).
9. ~~Company catalogue, `jobradar companies verify`, suggestions from alerts~~ — done in 2g;
   36 verified UAE-hiring companies approved and in the catalogue (US-2.7).
10. Golden datasets for India and UAE and conformance suite v1 (US-2.9).
New dependencies expected and needing approval when reached: Google API client (Gmail),
an HTML parser for alert emails, testcontainers (or compose services) for integration tests.

## Open questions/decisions waiting on me

- Save `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` in `.env` so the single verification call can run.
- Confirm `cryptography` as a direct dependency (token encryption).
- Google Cloud setup for Gmail (2f STOP).

## Known issues

- Phase 0 standards review marks environment separation, expanded health/recovery, queue
  reliability, telemetry propagation, CI security/coverage, integration testing, and operational
  security as partial or deferred in `PRODUCT_STANDARDS.md`.
- This checkout's ignored `.env` sets the host ports to PostgreSQL 5433 and Redis 6380 because
  unrelated containers already bind host ports 5432 and 6379. Docker maps these host ports to
  the containers' normal ports (5432 and 6379); do not stop the unrelated containers. Tests now
  disable `.env` loading so their results do not depend on these local overrides.
- The previous OneDrive checkout remains on disk and must not be used for future work.
- CI: the first run on the new setup failed (ruff formatted Markdown code blocks; a multi-hook
  pre-commit call). Fixed in `d31725a`, whose run passed. Dependabot may open update PRs.
- The plain-text resume parser is a placeholder until the LLM wrapper and PDF/DOCX parsing are
  available.
