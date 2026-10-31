# JobRadar — Job Search Operating System

> This file is the source of truth for how work is done in this repo. Any AI coding agent must
> read it fully before writing code, follow its rules, and work one phase at a time. Product and
> design detail lives in `docs/` (map in §3); when this file and a doc disagree, fix the doc or
> this file in the same change; never silently pick one.

## 1. What we are building

A job-search operating system for **anyone: any role, any country, any seniority**. It runs the
lifecycle: profile → discover → match → prepare → apply → track → follow up → interview → offer → learn.
Everything that differs by country, field, role, persona, language or source is **config (packs,
policies) or a registered plug-in**. Adding a country or role needs no core code changes.

- **Rollout:** design for everyone, launch with one user (Stage 1: the owner), then friends
  (Stage 2: invite-only), then the public (Stage 3). Code is multi-tenant-correct from day one.
- **First configuration (user #1):** India + UAE, Java backend, persona/seniority `mid`. It is a
  configuration, not the scope.
- **Surfaces:** the **web app (PWA)** is the main product; the **browser extension** handles
  logged-in portals with the user in control; **email, web push and Telegram** are optional
  notification channels; the **home runner** is an optional power-user mode; the CLI is for
  developers and the operator.
- **North star:** interviews per week per active user.

## 2. Non-negotiable rules

1. **Never fabricate.** The LLM may only reorder and rephrase facts in the profile and answer bank.
   Unknown screening question → pause the application and ask the user; save the answer for reuse.
   Nothing about a user is inferred (credentials, visa status, sensitive fields).
2. **Dry-run by default.** Every apply adapter supports `dry_run=True` (fill, screenshot, no
   submit). Live submission needs the lane enabled, `apply.live_submit.enabled`, a recorded dry-run
   review for that user, and every guard passing at submit time.
3. **Caps, quality and kill switch.** Per-lane daily caps, per-user ceilings, per-employer caps,
   minimum fit ≥ global floor, human-like delays. `PAUSE_ALL` (global) and per-user pause stop all
   apply activity immediately. Guards are re-checked immediately before submit. JobRadar must never
   be usable to spam employers (PRD §7.1).
4. **Source policies decide automation.** `config/source_policies.yaml` lists allowed access modes
   per host; unknown hosts are `one_tap` only. **LinkedIn, Indeed, Bayt, Naukrigulf and GulfTalent
   are one-tap only:** no submit, fill or scraping code. The extension never reads, fills or clicks
   anything on those pages (side panel with copy buttons only).
5. **Credentials never enter the repo or the cloud.** Secrets in `.env` (git-ignored). Portal
   sessions stay in the user's own browser (extension) or home machine (runner); cookies are never
   uploaded.
6. **Proof of every submission:** screenshot + JSON snapshot of submitted data + prompt/model
   versions.
7. **Respect sources.** Official/public APIs and alert emails first; cache; rate-limit politely;
   clear User-Agent; SSRF guard on every outbound fetch.
8. **Every module has tests.** Connectors and parsers are tested against saved fixtures and golden
   datasets, never live sites. LLM calls in CI use recorded responses.
9. **Tenant isolation.** Every user-owned table has `user_id` and RLS; every service and
   repository call takes a `UserScope`; another user's resource returns 404.
10. **Privacy by design (DPDP Act, GDPR).** Explicit consent per data source, minimal data, no PII in
    logs, export and full deletion. No third party learns what users view: the web app and
    extension load images, fonts and scripts only from our origin (logos via our caching proxy);
    emails contain no remote images or tracking pixels.
11. **Untrusted input stays data.** Job posts, emails and page content are never interpolated into
    prompt instructions, never rendered as HTML, never logged; the LLM can never trigger a
    submission.
12. **Nothing project-related lives only in a scratch folder.** Scripts, reports and generated
    artifacts that matter are saved in the repo (one-offs worth keeping go to `scripts/archive/`
    with a note) or discarded on purpose. Say which in the progress update.
13. **Ask before adding a dependency** not listed in §4, and record the approval in
    `docs/decisions-log.md`.
14. **Durable project memory, every step.** At the end of every step or task: update
    `docs/progress.md` (and `docs/decisions-log.md` if a decision was made), **commit with a
    conventional commit message, and push**. At the start of every session: read this file,
    `docs/progress.md` and `docs/decisions-log.md`, then summarise the state before doing anything.

## 3. Documentation map

| Doc | What it holds |
|---|---|
| `docs/prd.md` | Problem, personas, goals, market/role/persona model, surfaces, experience quality, trust and fair use, **user stories by phase (US-x.y)**, multi-market quality gates, metrics, risks |
| `docs/architecture.md` | HLD: context, containers, frontend delivery, auth, tenancy, layering, queues, quotas, tiered matching, data flow, failure modes, scaling path, cost model, quality gates |
| `docs/adr/` | ADR-0001 … ADR-0025 (index in `docs/adr/README.md`) |
| `docs/lld/` | One design per module + `database.md` (tables, RLS, migration rules, **per-phase schema plan**) + `state-machine.md`; `README.md` has shared types, canonical identifiers and the story → module → table → endpoint traceability table |
| `docs/api.md`, `docs/openapi.yaml` | API rules and the hand-maintained OpenAPI 3.1 contract (147 operations, each tagged with its phase) |
| `docs/coding-standards.md` | Coding rules and how each is enforced |
| `docs/design-system.md`, `docs/ux.md` | Brand "Calm Compass", tokens, components, motion; journeys and screens |
| `docs/PRODUCT_STANDARDS.md` | Quality bar A–Z |
| `docs/progress.md`, `docs/decisions-log.md` | Project memory |

## 4. Tech stack

| Concern | Choice |
|---|---|
| Language | Python 3.12 (`uv`); TypeScript (`pnpm`, Node LTS) for the frontend |
| API | FastAPI, `/api/v1`, problem details (RFC 9457) |
| DB | PostgreSQL 16 with **pgvector** (`pgvector/pgvector:0.8.0-pg16`), SQLAlchemy 2.x (typed, async), Alembic, row-level security |
| Queue + schedules | Redis + Celery + Celery Beat (queues: discovery, llm, apply, email, notify, default) |
| Validation / settings | Pydantic v2, pydantic-settings |
| Browser automation | Playwright (Chromium) for server-side dry-run/apply on allowed ATSs |
| HTTP | httpx (async, via `core.http` only), tenacity |
| LLM | LiteLLM behind `core.llm` gateway; model tiers small/standard/premium/embedding; tiered matching (ADR-0023) |
| Web app | React + TypeScript (Vite), Tailwind, shadcn/ui on Radix, Motion, TanStack Query, Lucide, Recharts, Storybook; installable PWA. **No Streamlit.** |
| Extension | Manifest V3 (Chromium first, Firefox next), shares tokens/UI packages |
| Notifications | Outbox + channels: in-app, email (transactional provider), web push (VAPID), Telegram (python-telegram-bot) |
| Email ingestion | Gmail API read-only (Stages 1–2); per-user forwarding address (Stage 3) |
| Documents | python-docx, WeasyPrint (RTL-capable) |
| Quality | ruff (format + broad rule set), mypy strict on all of `src/`, import-linter, pytest + pytest-cov, pre-commit, Playwright visual regression, Lighthouse CI |
| CI/CD | GitHub Actions (SHA-pinned), pip-audit and openapi-spec-validator via `uvx`, gitleaks, Dependabot |
| Deploy | Docker Compose (Stages 1–2) behind Caddy; ops stack: Prometheus, Grafana, Loki, Uptime Kuma, GlitchTip |
| Logging | structlog JSON, correlation IDs, no PII |

Approved but deferred to the phase that needs them: auth libraries (argon2, OIDC, TOTP), transactional
email and web-push libraries (Phase 4 approval), `pypdf` (resume parsing).

## 5. Repository layout

```
jobradar/
├── CLAUDE.md · AGENTS.md · README.md · pyproject.toml · uv.lock · docker-compose.yml · .env.example
├── .github/            workflows/ci.yml, dependabot.yml, pull_request_template.md
├── config/             profile.example.yaml, answer_bank.example.yaml, companies.yaml,
│                       source_policies.yaml, connectors.yaml, alert_senders.yaml,
│                       compensation/<market>/<date>.yaml, consents/   (profile.yaml is git-ignored)
├── packs/              markets/, roles/, personas/   (validated YAML)
├── alembic/            migrations (one per phase, docs/lld/database.md §9)
├── src/jobradar/
│   ├── core/           settings, db, logging, errors, scope, clock, ids, http, llm, queue, flags,
│   │                   plugins, packs, crypto
│   ├── models/         SQLAlchemy tables
│   ├── accounts/ privacy/ quotas/ profile/ connectors/ normalizer/ matching/ documents/
│   │   apply/ lifecycle/ notify/ strategy/ insights/ runner/ admin/
│   │                   each: __init__.py (public API), service.py, repository.py, schemas.py,
│   │                   rules.py, plugins/ — created only when needed
│   ├── api/            FastAPI app + routers (thin)
│   ├── tasks/          Celery tasks (thin) + celery_app entry point
│   └── cli.py
├── frontend/           (Phase 4) packages/{tokens,ui,api-client,i18n}, apps/{web,extension}
├── tests/              unit/, integration/, golden/<market>/, conformance/, synthetic/,
│                       contract/, isolation/, fixtures/
├── scripts/archive/    kept-for-the-record scripts (not run, not linted)
└── docs/               see §3
```

## 6. Data model and state machine (summary)

Full definitions: `docs/lld/database.md` (≈ 45 tables, RLS, constraints, retention, migration
rules) and `docs/lld/state-machine.md`.

- **Shared corpus (no personal data):** companies, jobs, job_sources, job_embeddings,
  source_runs, plans.
- **User-owned (RLS):** users, profiles, profile_embeddings, resume_variants, answer_bank, files,
  consents, alert_inboxes, alert_messages, job_scores, job_feedback, applications,
  application_events, apply_attempts, pending_questions, document_renders, emails, interviews,
  offers, contacts, notifications, search_plans, metrics_daily, usage_counters, … .
- **Application states:** `matched → queued → applied → acknowledged → assessment → interview →
  offer → hired | declined`, with `skipped`, `failed`, `rejected`, `ghosted`, `withdrawn`.
  Sub-states in `state_reason`. Lanes: `auto`, `careful`, `assisted`, `one_tap`.
- Transitions only via `lifecycle.transition()` (the only writer of `applications.state`); every
  transition writes an `application_events` row; `ghosted` after N days (default 21, per user).
- **Schema is incremental:** each phase's migration creates only the tables that phase needs
  (`database.md` §9).

## 7. Components (summary)

Module responsibilities, interfaces and tests are in `docs/lld/<module>.md`. Layering:
entry points (`api`, `tasks`, `cli`) → domain services → repositories → models → `core`
(import-linter enforced). Domains call each other only through their public `__init__.py`.

- **connectors:** ATS boards (Greenhouse, Lever, Ashby, Workable, SmartRecruiters), Adzuna,
  Remotive; job-alert emails (LinkedIn, Naukrigulf, Bayt, GulfTalent) via `AlertInbox`; company
  catalogue; source policies; logo proxy.
- **normalizer:** dedupe, rules-first normalization, small-model LLM fallback, taxonomy,
  compensation models (India new/old regime, UAE tax-free monthly), FX, shared job embeddings.
- **matching:** tiered pipeline: rules/eligibility → embedding similarity → batched LLM top N →
  ranking with reasons.
- **documents / apply:** variants per market format, facts-only tailoring with claim check;
  adapters with dry-run, proof, unknown-question flow, one-tap packs, extension assist plans.
- **lifecycle:** state machine, inbox tracking (consent), follow-ups, ghosting, interviews, offers,
  contacts.
- **notify:** outbox, channels, digest, preferences, quiet hours.
- **strategy / insights:** search plan and weekly re-plan (user approves); funnel, KPIs, weekly
  report.
- **accounts / privacy / quotas / admin / runner / extension:** auth and tokens; consent, export,
  deletion; plans, budgets, anti-abuse; operational console; optional runner; browser extension.

## 8. Packs (config, not code)

Market, role and persona packs are validated by Pydantic on load (PRD §4). Market packs cover
money, language/RTL, CV norms and field defaults, visa routes, sources with access modes,
notice norms, credential recognition and `last_verified` (stale > 90 days → warning). Role packs
use the field → family → role taxonomy with per-market credentials and hiring patterns. Persona
packs set channel weights, volume, tailoring depth, follow-up days and defaults. **Every pack
must pass the conformance suite before its `market.<code>.enabled` / `role.<code>.enabled` flag
can be turned on** (PRD §8a).

## 9. Schedules (Celery Beat; per-user times are in each user's time zone)

A dispatcher runs every 15 minutes and enqueues per-user tasks whose local time is due.

| Task | When |
|---|---|
| `discover_all` (shared corpus) + `ingest_alerts[user]` | every 2 hours |
| `normalize_new` → `embed_jobs` → `match_user[profile]` | after each discovery run |
| `auto_apply_batch[user]` | 10:00, 14:00, 18:00 local |
| `inbox_sync[user]` (Phase 6, consented) | every 15 min |
| `daily_digest[user]` | 08:00 local (user preference), delivered by 08:15 |
| `followups_and_ghosting[user]` | 09:00 local |
| `weekly_insights[user]` + re-plan proposal | Sunday 19:00 local |
| `refresh_sponsor_registers` | weekly |
| `quota_rollup`, `abuse_scan` | nightly / daily |
| `refresh_logo[company]` | on cache miss, at most every 30 days |
| backups + restore test (Phase 7) | nightly / monthly |

## 10. Build phases (in order; each must meet its acceptance criteria)

Stories and their acceptance criteria are in `docs/prd.md` §8. Stage 1 = Phases 2–7, Stage 2 =
Phases 8–10, Stage 3 = Phase 11.

- **Phase 0 — Scaffold.** ✅ Done.
- **Phase 1 — Profile & packs.** ✅ Done (pack-schema follow-ups start Phase 2).
- **Phase 2 — Discovery.** Pack schema extensions (US-1.2 AC2/AC3), ATS connectors (Greenhouse,
  Lever, Ashby, Workable, SmartRecruiters), Adzuna, Remotive, Gmail job-alert ingestion and parsers,
  dedupe, `source_runs` and health, company catalogue + verify + suggestions, source policy
  registry, golden datasets and conformance v1. ✅ `jobradar discover` stores fresh deduplicated
  jobs from every source including alerts; fixture/golden tests per connector and parser;
  conformance green for India and UAE; ≥ 30 verified UAE-hiring companies.
- **Phase 3 — Normalize & match.** Normalizer, taxonomy, compensation models + FX, LLM gateway with
  metering and budgets, profiles in the DB, resume draft parsing, embeddings, tiered matching,
  eligibility, ranking, synthetic users. ✅ `jobradar matches --top 20` with reasons and pay
  comparison; synthetic users green; cost per user reported.
- **Phase 4 — Web app foundation & notifications.** Tokens + Storybook design system, sign-in with
  TOTP for the owner, Today / Jobs / Job detail, digest on chosen channels (email, push,
  Telegram), pause, flags, admin basics, logo proxy, UI test matrix. ✅ The owner receives the 08:00
  digest with real matches and acts from the web app or Telegram; Lighthouse ≥ 90; visual
  regression baseline.
- **Phase 5 — Documents & apply (dry-run).** Variants, tailoring with claim check, Greenhouse/Lever/
  Ashby (then Workable/SmartRecruiters) adapters in dry-run, unknown-question flow, one-tap packs.
  ✅ Dry-run on 5 real jobs produces correct screenshots.
- **Phase 6 — Live apply + lifecycle.** Live submit behind flags and dry-run review, inbox tracking,
  follow-ups, ghosting, contacts, pipeline board, interview/offer records. ✅ A real application is
  tracked end-to-end from email.
- **Phase 7 — Deploy (Stage 1 complete).** Production compose, cloud VM, Caddy, backups and restore
  test, monitoring, alerts, runbooks. ✅ Runs unattended for 7 days.
- **Phase 8 — Browser extension (Stage 2 starts).** Pairing, assisted apply on allowed ATSs with
  proof, side panel on one-tap hosts, optional home runner. ✅ Assisted apply with proof; manifest
  test against source policies passes.
- **Phase 9 — Strategy, insights, interviews, offers.** ✅ Weekly report and approved re-plan;
  interview prep; offer comparison across INR and AED.
- **Phase 10 — Multi-user readiness (friends).** Invites, onboarding wizard, consent centre,
  isolation suite, quotas and plans, anti-abuse, export and deletion, admin console, next market and
  role packs behind rollout flags. ✅ A second user cannot reach the first user's data through any
  endpoint or task; friends onboard by invite.
- **Phase 11 — Public launch (Stage 3).** Landing page, legal documents, open signup, forwarding
  inbox, Arabic shipped, load test. ✅ SLOs hold with 1,000 synthetic users.

## 11. How every phase and story is built

For each story, in this order:
1. **PRD story:** start from its US-x.y and acceptance criteria in `docs/prd.md`.
2. **Check the LLD:** read the module design(s) from the traceability table in
   `docs/lld/README.md`, plus `database.md` §9 for the phase's tables and `docs/openapi.yaml` for
   endpoints. If the design is wrong or incomplete, fix the doc first (and log the decision).
3. **Code:** within the layering and standards; only the tables, settings and endpoints of the
   current phase.
4. **Tests:** unit, fixture/golden, conformance, synthetic and isolation tests as the LLD's test
   plan lists; coverage gates must hold.
5. **Self-review** against `docs/coding-standards.md`, `docs/PRODUCT_STANDARDS.md` and the PR
   template checklist; run `uv run pre-commit run --all-files`.
6. **Update `docs/progress.md`** (and `docs/decisions-log.md` if anything was decided).
7. **Commit** (Conventional Commits) and **push**. Check CI.

A phase is done only when its acceptance criteria are met and demonstrated, the README section is
updated, and a CHANGELOG entry is written.

## 12. Coding conventions

`docs/coding-standards.md` is binding and tool-enforced: ruff (complexity ≤ 10, Google docstrings,
security, async, banned APIs), mypy strict on all of `src/`, import-linter layering, custom
`JobRadarError` hierarchy with no bare or blind `except`, timeouts on all I/O, no blocking calls in
async code, no magic numbers or hardcoded URLs, structlog with no PII, test markers and naming,
coverage ≥ 80 % (overall and critical packages), Conventional Commits, PR template. No secrets,
personal data or real resumes are committed; use `*.example.*` files and synthetic data.
