# JobRadar — Personal Job Search Operating System

> This file is the source of truth for the project. Any AI coding agent working in this repo
> must read it fully before writing code, follow its rules, and work one phase at a time.

## 1. What we are building

A self-hosted system that runs a job seeker's entire search lifecycle:

profile → discover → match → prepare → apply → track → follow up → interview → offer → learn

It serves India plus international, country-specific and remote markets, and adapts its
strategy to the candidate's profile (persona, seniority, role, target markets).

Primary user: one person (the owner). Architecture must still be multi-user-ready
(every user-owned table has `user_id`), but build single-user UX first.

## 2. Non-negotiable rules

1. **Never fabricate.** The LLM may only rephrase facts that exist in the profile / answer bank.
   Unknown screening questions → pause the application and ask the user via Telegram.
   Save the answer to the answer bank for reuse.
2. **Dry-run by default.** Every apply adapter supports `dry_run=True` (fill, screenshot, do not submit).
   Live submission requires `dry_run: false` in config AND the lane being enabled.
3. **Caps and kill switch.** Every lane has a daily cap and human-like random delays.
   A global `PAUSE_ALL` flag (DB + Telegram `/pause`) stops all apply activity immediately.
4. **No automation of LinkedIn Easy Apply or Indeed Apply.** These lanes are "one-tap":
   the system prepares everything and sends the user a link. Do not write submit code for them.
5. **Credentials never enter the repo or the cloud.** Secrets in `.env` (git-ignored).
   Portal logins live only in the home runner's local browser profile.
6. **Proof of every submission:** store a screenshot + JSON snapshot of all submitted data.
7. **Respect sources.** Use official/public APIs where they exist, cache responses,
   rate-limit politely, set a clear User-Agent.
8. **Every module has tests.** Connectors are tested against saved fixture responses, not live sites.
9. **Durable project memory.** At the end of every task: update `docs/progress.md` (and
   `docs/decisions-log.md` if a decision was made), commit, and push. At the start of every new
   session: read `CLAUDE.md`, `docs/progress.md` and `docs/decisions-log.md`, then summarize the
   state before doing anything.

## 3. Tech stack

| Concern | Choice |
|---|---|
| Language | Python 3.12, managed with `uv` |
| API | FastAPI |
| DB | PostgreSQL 16, SQLAlchemy 2.x (typed), Alembic migrations |
| Queue + schedules | Redis + Celery + Celery Beat |
| Validation / settings | Pydantic v2, pydantic-settings |
| Browser automation | Playwright (Chromium) |
| HTTP | httpx (async), tenacity for retries |
| LLM | Provider-agnostic wrapper (LiteLLM) — default free tier (Gemini or Groq), swappable via config |
| Bot | python-telegram-bot |
| Email | Gmail API (OAuth, read-only scope to start) |
| Dashboard (v1) | Streamlit (replace with a proper web app later) |
| Docs generation | python-docx / WeasyPrint for resume variants |
| Quality | ruff, mypy (strict on `core/`), pytest, pre-commit |
| Deploy | Docker Compose (api, worker, beat, bot, postgres, redis, dashboard) |
| Logging | structlog, JSON logs |

## 4. Repository layout

```
jobradar/
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── docker-compose.yml
├── .env.example
├── config/
│   ├── profile.example.yaml      # user profile, preferences, lanes, caps
│   ├── companies.yaml            # target companies: name, ats, slug, country
│   └── answer_bank.example.yaml  # reusable screening answers
├── packs/
│   ├── markets/                  # india.yaml, us.yaml, uk.yaml, germany.yaml, uae.yaml, remote.yaml ...
│   ├── roles/                    # software_engineer.yaml, data_analyst.yaml, designer.yaml ...
│   └── personas/                 # fresher.yaml, mid.yaml, senior.yaml, switcher.yaml, mover.yaml ...
├── data/
│   └── registers/                # public visa sponsor registers (UK, NL), refreshed by a job
├── src/jobradar/
│   ├── core/                     # settings, db session, base models, logging, llm wrapper, packs loader
│   ├── models/                   # SQLAlchemy models
│   ├── profile/                  # resume parsing, persona inference, answer bank
│   ├── connectors/               # base.py + one file per source
│   ├── normalizer/               # seniority, remote type, salary, visa, ghost/scam scoring
│   ├── matching/                 # eligibility filters, AI fit score, ranking
│   ├── documents/                # resume variants, tailoring, cover notes
│   ├── apply/                    # base adapter + greenhouse, lever, ashby, workable adapters
│   ├── lifecycle/                # state machine, inbox tracker, follow-ups, interviews, offers
│   ├── strategy/                 # profile + packs → search plan; weekly re-planning
│   ├── insights/                 # analytics, weekly report
│   ├── notify/                   # telegram bot, digest builder
│   ├── tasks/                    # celery app + scheduled tasks
│   ├── api/                      # FastAPI routers
│   └── runner/                   # home runner client (runs on user's machine, pulls tasks)
├── dashboard/                    # streamlit app
└── tests/
    ├── fixtures/                 # saved API responses per connector
    └── ...
```

## 5. Data model (core tables)

- `users` — id, name, email, timezone (default Asia/Kolkata)
- `profiles` — user_id, persona, seniority, years_exp, skills (jsonb), target_markets, target_roles,
  locations, salary_expectations (per currency), notice_period_days, visa_status (per country), languages
- `resume_variants` — profile_id, name, market_format (in/us/de/...), role_focus, file_path, structured_content (jsonb)
- `answer_bank` — user_id, question_canonical, question_variants (array), answer, scope (global/market/company)
- `companies` — name, domain, ats, ats_slug, countries, sponsor_flags (jsonb: uk_licensed, nl_recognised, us_h1b_history), quality_score
- `jobs` — source, source_job_id, company_id, title, description, url, apply_url, location_raw, posted_at, raw (jsonb),
  normalized fields: seniority, role_family, remote_type (onsite/hybrid/remote_country/remote_region/remote_global),
  allowed_regions, country, salary_min/max, currency, salary_annual_inr, visa_sponsorship (yes/no/unknown + confidence),
  language_required, ghost_score, scam_score, dedupe_hash, first_seen_at, last_seen_at
- `job_scores` — job_id, profile_id, eligible (bool), eligibility_reasons, fit_score (0–100), matched_skills, missing_skills, rationale, model, created_at
- `applications` — job_id, profile_id, lane (auto/careful/one_tap), state, resume_variant_id, submitted_payload (jsonb),
  screenshot_path, applied_at, last_event_at
- `application_events` — application_id, from_state, to_state, trigger (system/email/user), detail, created_at
- `emails` — gmail_id, thread_id, from, subject, received_at, classification, application_id (nullable), extracted (jsonb)
- `contacts` — company_id, name, role, linkedin_url, relation (recruiter/hiring_manager/alumni/referrer), notes
- `interviews` — application_id, round, type, scheduled_at, prep_pack (jsonb), outcome, notes
- `offers` — application_id, base, variable, joining_bonus, equity, currency, ctc, in_hand_monthly_est, joining_date, deadline
- `source_runs` — connector, started_at, finished_at, jobs_found, jobs_new, errors
- `settings_flags` — key/value (PAUSE_ALL, lane toggles) editable from Telegram

## 6. Application state machine

```
discovered → matched → queued → applied → acknowledged → assessment → interview → offer
                         │          │            │              │            │
                         └→ skipped └→ failed    └→ rejected / ghosted / withdrawn (from any active state)
```
- Transitions only via `lifecycle.state_machine.transition()`; every transition writes an `application_events` row.
- `ghosted` is set automatically after N days (configurable, default 21) with no events.

## 7. Components — responsibilities

**Connectors** (`connectors/base.py` defines `fetch() -> list[RawJob]`):
Greenhouse, Lever, Ashby, SmartRecruiters, Workable (public job-board endpoints, per company in `companies.yaml`),
Adzuna (multi-country API), Remotive, Arbeitnow, RemoteOK (if terms allow), email-alert parser (job alert emails from portals).
Each connector: async, retries, rate limit, writes a `source_runs` row, fixture-based tests.

**Normalizer:** rule-based first, LLM only for fields rules can't resolve. Outputs the normalized job fields above.
Dedupe via hash of (normalized company, normalized title, country, city).

**Matching:** 1) hard eligibility (location/remote region, visa, language, experience range, excluded keywords);
2) LLM fit score with structured JSON output; 3) rank = fit × freshness × company quality × strategy weight.

**Documents:** resume variant selection per market + role; tailoring limited to reordering and rephrasing true facts;
output docx/pdf; store which variant went to which application.

**Apply adapters** (`apply/base.py`: `prepare(job) -> FormPlan`, `fill(plan, dry_run) -> Result`):
fetch form schema where the ATS exposes it, map fields to profile + answer bank, collect unknown questions,
upload resume, screenshot, submit only when allowed.

**Lifecycle / inbox:** poll Gmail every 15 min, classify emails (acknowledgement, assessment, interview invite,
rejection, recruiter outreach, offer, other), link to application by company/job title, trigger transitions,
extract deadlines and meeting links.

**Notify (Telegram):** daily digest 08:00 IST; per-job buttons (Apply / Skip / Save); unknown-question prompts;
commands: /pause, /resume, /status, /today, /stats.

**Strategy:** reads profile + packs → produces a `SearchPlan` (markets, roles, sources, lanes, daily caps,
min fit score). Re-plans weekly from insights.

**Insights:** callback rate by source, market, resume variant, lane; weekly Telegram report.

**Runner (home):** small client on the user's machine; authenticates to API with a token, pulls tasks for
logged-in portals, executes with a persistent local Playwright profile, reports results. Never uploads cookies.

## 8. Packs (config, not code)

Market pack fields: `code, name, currency, job_boards, cv_format, photo_on_cv, salary_convention,
visa_routes (name, summary, sponsor_required), sponsor_register_source, notice_period_norm,
language_notes, last_verified`.
Role pack fields: `code, title_aliases, core_skills, signal_documents (portfolio/github/...), assessment_types, resume_emphasis`.
Persona pack fields: `code, description, channel_weights, daily_volume_range, resume_strategy, tips`.
Packs are validated with Pydantic schemas on load. `last_verified` older than 90 days → warning in logs.

## 9. Schedules (Celery Beat, Asia/Kolkata)

| Task | When |
|---|---|
| discover_all | every 2 hours |
| normalize_and_score_new | after each discovery run |
| auto_apply_batch | 10:00, 14:00, 18:00 |
| inbox_sync | every 15 min |
| daily_digest | 08:00 |
| followups_and_ghosting | 09:00 daily |
| refresh_sponsor_registers | weekly |
| weekly_insights | Sunday 19:00 |

## 10. Build phases (do them in order; each must meet its acceptance criteria)

- **Phase 0 — Scaffold:** repo layout, uv, ruff/mypy/pytest/pre-commit, settings, logging, docker-compose with
  postgres + redis, Alembic, health endpoint. ✅ `docker compose up` works; `pytest` passes.
- **Phase 1 — Profile & packs:** profile.yaml + answer bank loaders, pack schemas, India + 1 target market + 1 role pack,
  resume parser to structured profile. ✅ CLI `jobradar profile show` prints validated profile.
- **Phase 2 — Discovery:** connector base + Greenhouse, Lever, Ashby, Adzuna, Remotive; jobs table; dedupe; source_runs.
  ✅ CLI `jobradar discover` stores fresh jobs; fixture tests for each connector.
- **Phase 3 — Normalize & match:** normalizer, eligibility filters, LLM fit score, ranking. ✅ `jobradar matches --top 20`.
- **Phase 4 — Telegram:** bot, daily digest, buttons, /pause. ✅ digest arrives with real matches.
- **Phase 5 — Documents & apply (dry-run):** resume variants, tailoring, Greenhouse/Lever/Ashby adapters in dry-run,
  screenshots, unknown-question flow. ✅ dry-run on 5 real jobs produces correct screenshots.
- **Phase 6 — Live apply + lifecycle:** enable live submit behind flags, state machine, Gmail inbox tracker,
  follow-ups, ghosting. ✅ real application tracked end-to-end from email.
- **Phase 7 — Deploy:** production compose, cloud VM, backups, monitoring. ✅ runs unattended for 7 days.
- **Phase 8 — Home runner:** runner client + task queue; Naukri careful lane with caps; one-tap lane for LinkedIn/Workday.
- **Phase 9 — Strategy, insights, interviews, offers, dashboard.**

## 11. Coding conventions

- Type hints everywhere; Pydantic models at module boundaries.
- Small, pure functions in normalizer/matching so they're easy to test.
- No secrets, personal data or real resumes committed; use `*.example.*` files.
- Each phase ends with: tests passing, README section updated, a short CHANGELOG entry.
- Ask before adding a dependency not listed in section 3.
