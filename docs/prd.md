# JobRadar — Product Requirements Document (PRD)

| | |
|---|---|
| Status | Draft for owner review |
| Version | **0.4 (2026-10-30)**: tiered matching pipeline and cost target (ADR-0023); multi-market and multi-role quality gates, synthetic users, golden datasets, UI matrix, market rollout plan (ADR-0024); extension side panel on one-tap hosts; owner seniority = mid |
| Previous | 0.3: product for everyone (ADR-0013); web app + design system (ADR-0014, 0015); browser extension (ADR-0016); auth, privacy, quotas, i18n, taxonomy, source policies (ADR-0017 … 0022). 0.2: owner review of section 9; Gmail alert ingestion in Phase 2 |
| Source of truth | `CLAUDE.md` (rules, phases — updated in Step 7 to match this PRD), `docs/PRODUCT_STANDARDS.md` (quality bar) |
| First configuration | User #1 (owner): India + UAE, Java Backend, seniority set in profile |

Story IDs (`US-<phase>.<n>`) are stable. LLDs, tests and commits reference them. When a story
changes, edit it in place and note the change in `docs/decisions-log.md`. Stories that existed in
v0.2 keep their IDs; new stories get new IDs.

---

## 1. Problem statement

Looking for a job is stressful, slow and opaque for almost everyone, in every field and country:

- **Discovery is scattered.** Jobs are spread across company career pages, ATS boards, national
  and regional job boards, professional networks, recruiters and alert emails. No single place
  shows the relevant jobs once, without duplicates.
- **Markets work differently.** Each country has its own salary conventions (annual vs monthly,
  gross vs CTC vs package, taxed vs tax-free), work-authorization routes, CV norms (photo or no
  photo, one page or two, personal fields) and job sources. People moving countries are hit
  hardest.
- **Fields work differently.** A nurse needs a valid licence for the target country; a teacher
  hires to an academic calendar; a designer is judged on a portfolio; an engineer on GitHub and
  coding tests; a tradesperson on certifications and references; an executive through
  networks and search firms. Generic tools ignore this.
- **Eligibility is hidden.** Visa sponsorship, licence requirements, language, location and
  "residents only" restrictions are buried in descriptions. Good-looking jobs are dead ends.
- **Applying and tracking eat time.** Repetitive forms, screening questions, follow-ups and
  inbox triage take hours a week. Leads slip; applications go silent with no follow-up.
- **No feedback loop.** Job seekers can't see which sources, CV versions or approaches actually
  produce interviews.
- **Spray-and-pray tools make it worse.** Mass auto-apply tools flood employers, damage the
  candidate's reputation and lower everyone's response rates.

**JobRadar** is a job-search operating system for anyone — any role, any country, any
seniority. It runs the lifecycle *profile → discover → match → prepare → apply → track →
follow up → interview → offer → learn*. It automates only where that is safe, allowed and
wanted by the user; it never fabricates facts; it is built so it **cannot** be used to spam
employers.

**Rollout strategy (ADR-0013):** design for everyone, launch with one user (the owner), then
friends (invite-only), then the public. User #1's configuration (India + UAE, Java backend) is
the first configuration, not the scope.

## 2. Personas

Personas are **config (persona packs)**, not code. Onboarding infers a starting persona from
the user's answers; the user can change it any time. One user can combine traits (for
example "mid-level + international mover").

### 2.1 Primary personas by situation

| Code | Persona | Defining needs | Strategy emphasis |
|---|---|---|---|
| `student` | Student (internships, part-time, graduate schemes) | Little experience; academic calendar; campus programmes | Projects, coursework, internships; campus/graduate channels; deadlines |
| `fresher` | Fresher / new graduate | First full-time role; high volume tolerated | Skills + projects; entry-level filters; assessment prep |
| `mid` | Mid-level professional | Better role or pay | Balanced volume and tailoring; outcomes on CV |
| `senior` | Senior / lead | Fewer, better-fit roles | Low volume, deep tailoring, referrals, recruiters |
| `executive` | Executive (director, VP, C-level) | Confidential search; networks; search firms | Very low volume; contacts and search firms; board/leadership narrative; privacy defaults stricter |
| `switcher` | Career switcher | Changing field or role family | Transferable skills mapping; bridging credentials; adjacent-role targeting |
| `returner` | Returner after a break (caregiving, health, study, relocation) | Explaining a gap; confidence; returnship programmes | Gap framing (facts only, user-worded); returnship channels; refresher credentials |
| `mover` | International mover | Visa routes, credential recognition, CV norms, relocation | Sponsorship-aware eligibility; market CV formats; pay comparison across currencies |
| `remote` | Remote worker | Location-independent roles, time zones, contractor vs employee | Remote-region eligibility; time-zone overlap; global payroll/contract signals |
| `freelancer` | Freelancer / contractor | Contracts and fixed-term roles; day rates | Contract/temporary filters; day-rate normalization; agency contacts. Gig-marketplace bidding is out of scope (§10) |

### 2.2 Fields covered by the role taxonomy (§4)
Tech **and** non-tech: software & IT, data & analytics, design & creative, product & project
management, healthcare (nursing, allied health, physicians, pharmacy), finance & accounting,
education (school, higher education, training), sales & business development, marketing &
communications, operations & supply chain, customer service, hospitality & tourism, skilled
trades & construction, manufacturing & engineering (non-software), legal, human resources,
government & public sector, non-profit, science & research.

### 2.3 Operator personas
- **Owner** (role `owner`): runs the deployment; full control of flags, plans and admin.
- **Admin** (role `admin`): support and operations; sees operational data (connector health,
  queues, quotas, abuse flags) but **not** user content (resumes, emails, documents) unless the
  user grants time-limited support access, which is audit-logged.

### 2.4 User #1 (first configuration)
India-based Java backend engineer targeting India and the UAE. Persona `mid` (seniority
`mid`, confirmed 2026-10-30), with `mover` traits for the UAE. Prefers short mobile sessions.

## 3. Goals and non-goals

### Goals
- **G1 — More interviews.** Raise each user's interviews per week (north star) through better
  targeting, not volume.
- **G2 — One deduplicated feed** of relevant jobs per user, from public APIs, ATS boards,
  alert emails and user-saved jobs, refreshed every 2 hours.
- **G3 — Explainable matching:** eligibility with plain-language reasons, fit score 0–100,
  matched/missing skills and credentials, rationale.
- **G4 — Fair pay comparison** across currencies, periods and tax conventions, with every
  assumption shown.
- **G5 — Market- and field-correct documents:** CV variants per market × role; tailoring only
  reorders and rephrases true facts.
- **G6 — Safe applying:** dry-run by default, quality thresholds, caps, kill switch, proof of
  every submission, no duplicates, one-tap only where automation is not allowed.
- **G7 — Zero-effort tracking:** email-driven state changes, follow-up nudges, ghosting
  detection, interview prep.
- **G8 — Learning loop:** weekly insights feed a re-planned strategy.
- **G9 — Pluggable everything:** adding a country, role, persona, language or source needs
  packs, config and optional registered plug-ins — **no core code changes**.
- **G10 — Product for everyone:** self-serve signup, adaptive onboarding, per-user isolation,
  roles, usage limits, consent, export and deletion.
- **G11 — Premium experience:** a web app that feels at the level of Linear, Stripe or Notion —
  calm, fast, beautiful, accessible, localized and RTL-ready (§6).
- **G12 — Good citizen:** the product cannot be used to spam employers (§7).

### Non-goals
- Not a job board, marketplace, recruiter tool or employer-side ATS.
- No mass auto-apply. Volume is capped, quality-gated and strategy-driven.
- No automated submission, autofill or page scraping on platforms whose terms forbid it
  (LinkedIn, Indeed, and any host whose source policy says so).
- No generation of experience, skills, credentials, salaries, visa or licence statuses the user
  hasn't supplied.
- No legal, immigration, tax or licensing advice. Pack notes carry `last_verified` and links
  to official sources.
- No native mobile apps in v1 (installable PWA instead).

## 4. Configuration model: markets, roles, personas, sources

All variation lives in validated config (packs) and registered plug-ins (ADR-0006, ADR-0021).

### 4.1 Market packs (`packs/markets/<code>.yaml`)
Each country (or region such as `remote_emea`) is a pack with:
- **Money:** ISO currency, salary conventions (period: hourly/daily/monthly/annual; basis:
  gross/CTC/package/basic; common allowances; 13th/14th-month pay), `compensation_model` id.
- **Language & locale:** official/business languages, default locale, `rtl: true|false`,
  date/number formats.
- **CV norms:** format id, length norm, photo norm, personal fields on/off by default
  (`cv_fields_default_on`, `cv_fields_default_off`), section order, terminology ("CV" vs
  "résumé", "Lebenslauf").
- **Work authorization:** visa routes (name, summary, sponsor required, official link),
  sponsor-register source if public, nationality-restricted programmes to detect.
- **Job sources:** list of channels, each with an **access mode** from the source policy
  (`api`, `ats_feed`, `alert_email`, `extension_assist`, `one_tap`, `none`).
- **Norms:** notice period, hiring seasons, application-form conventions.
- **Credentials recognition:** links per field where licences must be recognised locally
  (for example nursing, medicine, teaching, law, engineering registration).
- **Provenance:** `last_verified`, sources; stale (> 90 days) → warning.

### 4.2 Role taxonomy and role packs (`packs/roles/`)
Three levels: **field → role family → role**. The backbone maps to a public occupational
classification (ISCO-08 groups; ESCO occupations where licensing allows — see ADR-0021) so
any title can be placed, while our role packs add job-search knowledge:
- `field`, `family`, `title_aliases` (multi-language), `core_skills`, `adjacent_roles`
  (for switchers).
- **Signal documents:** portfolio, GitHub, writing samples, case studies, publications,
  references.
- **Credentials:** `required_credentials` and `valued_credentials`, **per market** where they
  differ (licences, registrations, certifications, clearances), each with a verification note.
- **Hiring patterns:** volume vs referral driven, typical stages, assessment types (coding
  test, case study, practical/trade test, teaching demo, clinical assessment, portfolio
  review), seasonality (academic year, graduate intake, fiscal year), typical time-to-hire.
- **Resume emphasis:** what to put first for this field.

Examples (initial packs to author, in this order): `java_backend` (exists), `registered_nurse`,
`accountant`, `school_teacher`, `sales_executive`, `operations_manager`, `hospitality_supervisor`,
`electrician`, `data_analyst`, `product_designer`, `civil_servant` (generic public-sector).

### 4.3 Persona packs (`packs/personas/`)
`code, description, channel_weights, daily_volume_range, tailoring_depth, resume_strategy,
onboarding_steps, followup_days, default_llm_top_n, default_min_fit_score, tips`. Persona drives onboarding steps, strategy defaults and copy tone.

### 4.4 Source policy registry (`config/source_policies.yaml`, ADR-0022)
Every host/source has a policy: allowed access modes, rate limits, User-Agent, terms URL,
last reviewed date. The apply engine, connectors and extension **must** consult it.
LinkedIn and Indeed: `alert_email` + `one_tap` only. Gulf boards (Bayt, Naukrigulf,
GulfTalent): `alert_email` + `one_tap`. Public ATS boards: `ats_feed` (+ `extension_assist`
and server-side apply where the ATS allows).

### 4.5 First configuration: India + UAE (user #1)
These remain fully specified because they are the first packs to ship and test G9.

**India (`india`)** — INR; annual CTC with fixed/variable; in-hand estimate: CTC → fixed →
minus employee PF, professional tax and income tax → monthly; **new tax regime by default,
old regime optional** (`india_tax_regime`). Channels: (1) **job-alert emails — main India
source since Adzuna is paid and disabled in Stage 1** (Naukri, LinkedIn India, Instahyre, Foundit;
alert email + one-tap only); (2) ATS feeds for catalogued companies; (3) Adzuna when the paid plan
is taken (revisit before Stage 2–3); Naukri `extension_assist` only after a Phase 8 terms review. Warn when "immediate
joiner" conflicts with the notice period. CV format `in`; current/expected CTC only if opted in.

**UAE (`uae`)** —
- *Work authorization:* employer-sponsored work permit and residence visa. Per-country
  `visa_status` in the profile; postings' signals ("UAE residents only", "visa provided",
  "must be in UAE", "immediate joiner") extracted into `visa_sponsorship` + confidence;
  nationality-restricted (for example Emiratisation) roles marked ineligible with the reason.
- *Pay:* usually **monthly AED**, often a package (basic + housing + transport + allowances);
  **no personal income tax**. Stored with period, basis and annualized value. Comparison shows
  AED/month, AED/year, INR at a **manual dated rate** (`fx.aed_inr`, `fx.as_of`; later derived
  from USD→INR via the AED/USD peg ≈ 3.6725, held in config), and in-hand next to the India
  estimate. User-entered adjustments only; undisclosed figures are never estimated.
- *Channels:* (1) **job-alert emails — main UAE source** (LinkedIn, Naukrigulf, Bayt,
  GulfTalent); (2) **curated UAE-hiring companies** on Greenhouse/Lever/Ashby/Workable/
  SmartRecruiters; (3) recruiters and career pages (one-tap).
- *CV:* on by default — nationality, current location, visa status, notice period/earliest
  joining date. Off by default with a per-application toggle — photo, date of birth, marital
  status (only if supplied).
- *Notice period:* soft penalty in ranking unless the posting states a hard limit.

### 4.6 Adding a country or role (acceptance for G9)
A new market or role needs only: a pack that passes schema validation; optional source
entries + policies; optional sponsor-register loader; optional `CompensationModel`,
`EligibilityRule`, `AlertEmailParser`, `CvFormatter` plug-ins registered through entry
points; translations for any new UI strings. **No changes to core modules, models or
migrations.** A CI test loads every pack and runs the golden pipeline on fixture jobs per pack.

## 5. Product surfaces

| Surface | Role | Default |
|---|---|---|
| **Web app (PWA)** | The main product: onboarding, today view, feed, job detail, pipeline, documents, interviews, offers, insights, settings, admin console | Always on |
| **Browser extension** | Runs in the user's own browser for logged-in portals: show match and assist form fill on allowed ATS pages (user always clicks submit); on one-tap-only hosts, a side panel with prepared answers and copy buttons only | Recommended; optional |
| **Notifications** | Channels the user chooses: in-app, **email**, **web push** (PWA), **Telegram** | In-app + email digest on; others opt-in |
| **Home runner** | Optional mode for power users who want unattended logged-in tasks on their own machine | Off |
| **CLI** | Developer and operator tooling | Developers only |

Notification preferences are per channel and per event type (digest, unknown question,
interview invite, offer, follow-up due, weekly report), with quiet hours in the user's time
zone.

## 6. Experience quality (UI, look, feel, motion)

Detailed in `docs/ux.md` and `docs/design-system.md` (Step 6). These are product requirements,
not decoration:

- **E1 Brand:** confident, calm, encouraging. Voice: clear, warm, no jargon; never blames the
  user; celebrates progress, not volume.
- **E2 Stack (ADR-0014):** React + TypeScript (Vite), Tailwind, shadcn/ui on Radix, Motion,
  TanStack Query, Lucide icons, one chart library themed with tokens, Storybook, Playwright
  visual regression, Lighthouse CI. Installable, mobile-first PWA. **Streamlit is removed
  everywhere.**
- **E3 Design tokens (ADR-0015):** colour (light + dark, semantic), typography, spacing,
  radius, elevation, motion, breakpoints — as CSS variables + Tailwind theme. No hardcoded
  colours, sizes or durations in components (lint-enforced).
- **E4 Accessibility:** WCAG 2.2 AA — every text/background pair ≥ AA contrast, full keyboard
  use, visible focus, screen-reader labels, reduced motion respected.
- **E5 Internationalization (ADR-0020):** all strings externalized (ICU messages); locale-aware
  dates, numbers, currencies; full RTL (logical CSS properties, mirrored icons where meaningful);
  an Arabic-capable font alongside the variable UI font.
- **E6 Motion:** 150–300 ms, purposeful easing; page transitions, cards animating between
  pipeline columns, micro-interactions (press, apply success, score reveal, drag and drop),
  skeleton loaders (no spinners for content), subtle celebration for interviews and offers;
  `prefers-reduced-motion` → instant transitions.
- **E7 Interactivity:** drag-and-drop pipeline, command palette (Ctrl/⌘+K), keyboard shortcuts,
  instant search and filters, inline editing, optimistic updates, undo for destructive actions,
  helpful tooltips, swipe to apply/skip on mobile.
- **E8 Data visualisation:** funnel, callback rates, salary and offer comparison, weekly
  progress — consistent, token-coloured, accessible (patterns/labels, not colour alone).
- **E9 States:** every screen designed for loading, empty, error, success and offline; no
  layout shift (CLS < 0.1).
- **E10 Process:** design system built first in Storybook (every component in light/dark, all
  states, LTR and RTL) for owner review; screens built only from those components; CI runs
  visual regression and Lighthouse with budgets ≥ 90 for performance, accessibility and best
  practices.

## 7. Trust, safety and fair use

### 7.1 Anti-abuse: JobRadar can never be used to spam employers (ADR-0019)
Enforced server-side, not in the UI:
- **Quality threshold:** automated or assisted applications require eligibility = true and
  fit score ≥ the user's minimum, which can never be below a global floor (config).
- **Caps:** per-lane daily caps per user, a per-user global daily ceiling, and a
  **per-employer cap** (max applications to the same company in a rolling window). Global
  ceilings cannot be raised by plan or user setting.
- **No duplicates:** idempotency per (user, job) and per (user, employer, normalized title).
- **Human in the loop:** live automated submission is opt-in per lane and requires a completed
  dry-run review; LLM output never triggers a submission.
- **Signals and enforcement:** high rejection-without-response rates, bursty patterns or
  employer complaints → automatic cool-down; repeated abuse → suspension by admin.
- **Audit log:** every submission, flag change, quota change, export, deletion, consent change
  and support-access grant.
- **Employer contact:** a public abuse/contact address; reports are linked to the audit trail.

### 7.2 Usage limits and plans (ADR-0019)
- Per-user **quotas**: applications/day per lane, tailored documents/day, LLM tokens/day and
  /month (**LLM budget**), sources, alert emails ingested/day, storage.
- **Fair-use plans** as config (for example `free`, `supporter`, `friends_beta`); billing is
  out of scope until the public stage — plans only set limits.
- When a budget is reached: degrade gracefully (rules-only scoring, fewer tailored documents)
  and tell the user clearly; never silently stop core tracking.
- Deployment-wide LLM budget with alerts at 50/80/100%.

### 7.3 Privacy, consent and legal (ADR-0018)
- Aligned with India's **DPDP Act 2023** and **GDPR** principles: lawful purpose, consent,
  purpose limitation, data minimisation, retention limits, rights to access, correction,
  export and erasure; grievance contact.
- **Explicit consent per data source** (Gmail/alert inbox, extension, Telegram, each portal
  integration), stored with purpose, scope, timestamp and version of the consent text;
  revocable from settings with immediate effect (tokens revoked, ingestion stopped).
- **Data export** (JSON + CSV + documents) and **full account deletion** (hard delete of user
  content within a stated period; backups age out per retention policy).
- **Privacy policy and terms of service** published before the friends stage; consent text
  versioned; a change requires re-consent where material.
- Sensitive fields (photo, date of birth, marital status, nationality, health-related gap
  reasons) are optional, off by default and never inferred.
- Admins cannot see user content without user-granted, time-limited support access.
- **No third party learns what users view.** The web app and extension load images, fonts and
  scripts only from JobRadar's own origin; company logos are fetched server-side, cached, and
  served through our own proxy (`GET /companies/{company_id}/logo`), with an initials badge as
  fallback. Emails contain **no remote images** (no logos, no tracking pixels); companies are shown
  as coloured initials badges.
- **Email access at scale:** Gmail `readonly` is a restricted Google scope; public apps need
  Google verification and a periodic security assessment. Plan: Gmail API for user #1 and
  friends (within the unverified-app test-user limit), and a **per-user forwarding address**
  (user forwards alert emails to their private JobRadar inbound address) as the default for the
  public stage. Decision record: ADR-0018; inbound provider chosen at that phase.

## 8. User stories and acceptance criteria (by phase)

Phases follow the rollout: **Stage 1 — owner** (Phases 2–7), **Stage 2 — friends**
(Phases 8–10), **Stage 3 — public** (Phase 11). Every phase builds multi-user-correct code.
The phase list is mirrored into `CLAUDE.md` in Step 7.

### Phase 0 — Scaffold (done)
**US-0.1** As the operator, I want the stack to start with one command so I can develop locally.
- AC1: `docker compose up` starts PostgreSQL and Redis; `/health` and `/ready` respond.
- AC2: `uv run pytest`, ruff and mypy pass in CI.

### Phase 1 — Profile & packs (done; follow-ups at Phase 2 start)
**US-1.1** As a user, I want my profile validated so the system never works from bad data.
- AC1: `jobradar profile show` prints the validated profile; invalid fields show the field path.
- AC2: Per-country `visa_status`, salary expectations per currency and period, notice period,
  target markets and roles, nationality (optional), `india_tax_regime` (default `new`).

**US-1.2** As the operator, I want market, role and persona packs loaded and validated.
- AC1: India, UAE and `java_backend` packs load; `last_verified` missing or > 90 days logs a
  warning.
- AC2 (follow-up): `MarketPack` schema extended per §4.1 (currency conventions, locale/RTL, CV
  field defaults, sources with access modes, compensation model id); UAE pack lists LinkedIn,
  Naukrigulf, Bayt, GulfTalent with `alert_email`/`one_tap` modes.
- AC3 (follow-up): `RolePack` extended per §4.2 (field, family, credentials per market, hiring
  patterns); `PersonaPack` per §4.3.

**US-1.3** As a user, I want reusable screening answers with global, market and company scope.

**US-1.4** As a user, I want my PDF/DOCX resume parsed into a draft profile I confirm.
- AC1: Draft only; every field cites its source span; nothing is inferred.

### Phase 2 — Discovery
**US-2.1** ATS connectors (Greenhouse, Lever, Ashby, **Workable, SmartRecruiters**) for
companies in the catalogue.
- AC1: Async, retries with backoff, rate-limited per source policy, clear User-Agent.
- AC2: Each run writes `source_runs` (found, new, updated, errors, duration, HTTP statuses).
- AC3: Fixture-based tests; no live calls in tests.

**US-2.2** Aggregators (Adzuna for covered countries, Remotive for remote).
- AC1: Queries from role aliases × market locations; uncovered countries skipped with a logged
  reason.

**US-2.3** Deduplication across sources.
- AC1: Dedupe hash = normalized (company, title, country, city); repeat sightings update
  `last_seen_at` and add a `job_sources` row.

**US-2.4** `jobradar discover` runs discovery on demand.

**US-2.5** Job-alert email ingestion (main UAE source; generic for all markets).
- AC1: Gmail `readonly` scope; query restricted to configured alert senders/labels; token
  encrypted; consent recorded (US-10.3 model, minimal version now).
- AC2: One `AlertEmailParser` per sender format; anonymized `.eml` fixtures; format change →
  parser `degraded`.
- AC3: Parsed jobs keep the board link, record the alert source, route to the lane allowed by
  the source policy; message IDs make re-runs idempotent; raw bodies discarded after parsing.
- AC4: Inbox-based application tracking is not part of this story (US-6.2).
- AC5: Ingestion is behind an `AlertInbox` interface so a forwarding-address implementation
  (Phase 11) can replace Gmail without parser changes.

**US-2.6** Connector health: `degraded` on schema drift, 0 jobs, or > 70% drop vs 7-day average.

**US-2.7** Curated catalogue of employers per market, starting with UAE-hiring companies on
Greenhouse/Lever/Ashby/Workable/SmartRecruiters.
- AC1: `config/companies.yaml` validated (name, domain, ATS, slug, countries, source/notes).
- AC2: `jobradar companies verify` checks slugs politely (cached, fixtures in tests).
- AC3: Suggestions from employers seen in alerts go to a review list; nothing is added without
  confirmation.
- AC4: ≥ 30 verified UAE-hiring companies by end of Phase 2.

**US-2.8** Source policy registry (§4.4).
- AC1: Every connector and apply path reads its host's policy; a test fails if any connector
  or adapter has no policy entry.

**US-2.9** Golden datasets and conformance suite v1 (§8a.1, §8a.3).
- AC1: `tests/golden/india/` and `tests/golden/uae/` hold postings per connector format and alert
  emails per parser, with expected output; CI fails on any diff.
- AC2: The conformance suite runs the schema, currency, language, source-parsing checks for
  every pack in `packs/`; a pack failing any check cannot have its `market.<code>.enabled` flag
  turned on (enforced in the flag service).

### Phase 3 — Normalize & match
**US-3.1** Normalization (seniority, field/role family via taxonomy, remote type, location,
salary with period/basis, visa, language, required credentials, ghost/scam score).
- AC1: Rules first; LLM only for unresolved fields; strict schema + one repair retry.
- AC2: Salary stores original amount, currency, period, basis; annualized value; comparison
  currency computed at a dated rate.

**US-3.2** Eligibility with plain-language reasons: location/remote region, visa vs per-country
status, language, experience range, excluded keywords, nationality restrictions, **required
licences/registrations per market** (from role pack).
- AC1: Every ineligible job has at least one human-readable reason.

**US-3.3** AI fit score (0–100), matched/missing skills and credentials, rationale.
- AC1: Strict JSON; prompt version + model stored; job text treated as untrusted
  (prompt-injection test).

**US-3.4** Ranking: fit × freshness × company quality × strategy weight; `jobradar matches --top 20`.

**US-3.7 (tiered matching, ADR-0023)** As the operator, I want LLM scoring limited to each
user's best candidates so cost per user stays within target at Stage 3.
- AC1: Tier 0 — rules and hard eligibility filters run first, with no LLM.
- AC2: Tier 1 — embedding similarity between the user's profile embedding and **shared job
  embeddings computed once per job** (re-embedded only when the job's normalized text changes).
- AC3: Tier 2 — LLM fit scoring only for the user's **top N** Tier 1 candidates per run
  (`matching.llm_top_n`, default 10, per-plan limit), in **batches** (default 5 jobs per call
  sharing one profile context), using a compact structured job summary, not the full posting.
- AC4: Normalization and classification use a **cheaper model tier** (`llm.models.small`); fit
  scoring uses `llm.models.standard`; tailoring may use `llm.models.premium` only if the plan
  allows.
- AC5: Caching: a (job content hash, profile version, prompt version) score is never recomputed;
  normalization results cached per job content hash; identical prompts served from cache.
- AC6: Jobs below the Tier 2 cut still show a Tier 1 similarity-based "possible match" with a
  plain-language reason, and the user can request a full score (counted against their budget).
- AC7: Cost per active user is reported daily and stays at or below the target in §9.

**US-3.5** Pay comparison in the user's chosen comparison currency and period, with every
assumption (FX rate + date, tax model + regime, deductions) shown; "not disclosed" never
estimated. Implemented by per-market `CompensationModel` plug-ins (India and UAE first).

**US-3.8** Synthetic users end to end (§8a.2).
- AC1: `syn-01` … `syn-10` run discover (fixtures) → normalize → match in CI with expected
  eligible sets and reasons; documents, dry-run apply and digest stages are added as Phases 4–5
  land.
- AC2: Conformance checks for salary conversion and eligibility are added to the suite.

**US-3.6** Per-user LLM metering from the first LLM call.
- AC1: Every call records user (or `system` for shared normalization), tokens, cost estimate,
  latency, model, prompt version in `llm_calls`; per-user daily budget enforced (soft in Stage 1).

### Phase 4 — Web app foundation & design system
**US-4.1** As a user, I want a design system I can review in my browser before screens are built.
- AC1: Storybook with tokens and core components in light/dark, LTR/RTL, all states.
- AC2: Visual regression baseline in CI; token lint forbids raw colours/sizes/durations.

**US-4.2** As a user, I want to sign in securely (single user now, multi-user correct).
- AC1: Email + password (argon2) and Google sign-in; HttpOnly secure session cookie; CSRF
  protection; roles `user`/`admin`/`owner`; signup closed by flag in Stage 1.

**US-4.3** As a user, I want a today view, job feed and job detail.
- AC1: Feed with instant filters and search; job detail with eligibility reasons, score
  breakdown, pay comparison, Apply / Skip / Save; skeletons, empty, error, offline states.
- AC2: Lighthouse ≥ 90 (performance, accessibility, best practices) on these screens.

**US-4.4** As a user, I want a daily digest on the channels I choose (in-app, email, Telegram,
web push).
- AC1: Delivered by 08:15 in the user's time zone on 99% of days; each job shows title,
  company, market, fit score, one-line why, pay comparison if known, actions.
- AC2: Empty digest states why.

**US-4.5** As a user, I want to pause all apply activity instantly (web, Telegram `/pause`).
- AC1: After pause, no apply task starts; in-flight tasks re-check before submit and abort.

**US-4.6** As the owner, I want feature flags (global and per user) editable from the admin
console and Telegram, each change audit-logged.

**US-4.7** UI test matrix (§8a.4): PR smoke matrix (one LTR + one RTL locale, phone + desktop)
and nightly full matrix from the first screen onward.

### Phase 5 — Documents & apply (dry-run)
**US-5.1** Variant selection per market × role; variant stored on the application.
- AC3: Sensitive CV fields off by default; per-application toggle only if supplied; toggle
  state stored.

**US-5.2** Facts-only tailoring with claim-to-fact post-check; DOCX and PDF output; RTL
documents for RTL markets.

**US-5.3** Greenhouse/Lever/Ashby (then Workable/SmartRecruiters) server-side adapters in
dry-run with screenshots. AC: dry-run on 5 real jobs gives correct screenshots.

**US-5.4** Unknown screening question → application paused `awaiting_answer`; asked in app (and
on chosen channels); answer saved with scope; application resumes.

**US-5.5** One-tap packs (CV, cover note, answers, link) for one-tap sources; "I applied" moves
to `applied` with trigger `user`. No submit or autofill code for those hosts.

### Phase 6 — Live apply + lifecycle
**US-6.1** Live submit only when lane enabled + `dry_run: false` + under all caps + not paused +
quality threshold met (§7.1).
- AC1: All guards re-checked immediately before submit.
- AC2: Idempotency per (user, job) and per (user, employer, title).
- AC3: Screenshot + payload snapshot + prompt/model versions stored.

**US-6.2** Inbox tracking: classify application-related email and link to applications.
- AC1: Requires separate explicit consent (widening beyond alert senders), audit-logged.
- AC2: Events reflected within 20 min for 99% of emails; deadlines and meeting links extracted.

**US-6.3** Follow-up nudges; ghosting after N days (default 21).

**US-6.4** Recruiter outreach emails create/update contacts.

**US-6.5** Pipeline board: drag and drop between states with animation, optimistic update,
undo; invalid drops explained (state machine guards).

### Phase 7 — Deploy (Stage 1 complete)
**US-7.1** Runs unattended for 7 days on a cloud VM: TLS via Caddy, static web assets served
with long-cache headers, nightly encrypted backups, `make restore-test`, ops alerts with
runbooks.

### Phase 8 — Browser extension (Stage 2 starts)
**US-8.3** As a user, I want a browser extension that works in my own logged-in browser with me
in control.
- AC1: Manifest V3 (Chromium first; Firefox next); paired to the account through the web app
  with a scoped, revocable extension token; per-site permissions requested only for hosts whose
  source policy allows `extension_assist`.
- AC2: On allowed ATS pages: show match and eligibility, assist form fill from profile and
  answer bank, highlight unknown questions; **the user reviews and clicks submit**; the
  extension records proof (screenshot of the visible tab, payload snapshot) after the user
  submits.
- AC3: On `one_tap`-only hosts (LinkedIn, Indeed, Gulf boards) the extension **never reads,
  fills or clicks anything on the page**. It requests no host permission and injects no content
  script there. It may open the browser's **side panel** (extension UI, separate from the page)
  showing the prepared one-tap pack for a job the user selects from their JobRadar queue: answers,
  cover note, CV download, each with a **copy button**. The user pastes everything themselves.
  "Save this job" uses only the tab URL and title, read on the user's explicit click
  (`activeTab`), never page content.
- AC3a: An automated test asserts the built extension manifest has no host permissions or content
  script matches for any host whose source policy is `one_tap` only.
- AC4: Cookies and credentials never leave the browser.

**US-8.1** Optional home runner for unattended logged-in tasks (power users; off by default):
scoped token, pull model, caps, no cookie upload.

**US-8.2** One-tap flow for LinkedIn and Workday-hosted roles via the extension popup.

### Phase 9 — Strategy, insights, interviews, offers
**US-9.1** Weekly report (callback rate by source, market, CV variant, lane; interviews/week).
**US-9.2** Weekly re-plan proposed as a diff; applied only after user approval.
**US-9.3** Interview prep packs (company notes, field-specific assessment types, user's stories).
**US-9.4** Offer comparison across currencies, periods and tax models (base, variable,
allowances, bonus, equity, in-hand estimate, dates).
**US-9.5** Insights screen with token-themed charts (funnel, callback rates, weekly progress).

### Phase 10 — Multi-user readiness (friends, invite-only)
**US-10.1** Invite-only self-serve signup, email verification, password reset, optional TOTP
for admin/owner.
**US-10.2** Adaptive onboarding wizard by persona: resume upload → review draft → markets and
roles (with field-specific credential questions) → channels and consents → lanes and caps →
first matches preview.
**US-10.3** Consent centre: per-source consent with purpose and scope; revoke takes effect
immediately.
**US-10.4** Per-user isolation: a second user cannot read or change the first user's data
through any endpoint, task or extension call (automated test suite over every endpoint);
Postgres row-level security as defence in depth.
**US-10.5** Quotas and plans enforced (applications, documents, LLM budget, ingestion, storage);
clear in-app usage meter.
**US-10.6** Anti-abuse rules from §7.1 enforced and tested, including per-employer caps,
cool-downs and admin suspension.
**US-10.7** Data export and full account deletion; deletion verified by test.
**US-10.8** Admin console: users (no content), quotas, abuse flags, connectors, queues and dead
letters (replay), flags, LLM usage, audit log.
**US-10.9** Second and third market and role packs authored and passing the golden pipeline
test (proves G9).

**US-10.10** Market rollout: the next markets in the §8a priority list are enabled for friends
only after their rollout checklist is complete; each stays behind its feature flag until then.

### Phase 11 — Public launch (Stage 3)
**US-11.1** Landing page, privacy policy, terms, grievance contact; open signup with
rate-limited registration and abuse checks.
**US-11.2** Forwarding-address alert inbox as default; Gmail API only if Google verification is
completed.
**US-11.3** Full i18n with at least one RTL language (Arabic) shipped and reviewed.
**US-11.4** Load test: 1,000 synthetic users, discovery over 1,000 companies, SLOs held.
**US-11.5** Fair-use plans published; deployment-wide budgets and alerts.

## 8a. Multi-market and multi-role quality (ADR-0024)

India and the UAE are only the first launch markets. Every market, role and persona is held to
the same quality gates, so G9 is proven by tests rather than by claims.

### 8a.1 Pack conformance suite
Every market, role and persona pack must pass before it can be enabled. It runs in CI on every
change to `packs/`, `config/source_policies.yaml` or a plug-in.

| Check | Market pack | Role pack | Persona pack |
|---|---|---|---|
| Schema valid, `last_verified` ≤ 90 days, official links present | ✓ | ✓ | ✓ |
| Currency: ISO code, period/basis conventions, `CompensationModel` registered and round-trip tested | ✓ | | |
| Language/RTL: locales exist in i18n catalogues; `rtl` matches the locale; fonts cover the script | ✓ | ✓ (title aliases per language) | |
| CV format: `CvFormatter` renders a sample profile in DOCX and PDF; default-on/off fields honoured | ✓ | ✓ (emphasis order) | |
| Visa rules: each route has a summary, sponsor flag and link; eligibility rules produce reasons | ✓ | | |
| Credentials: required/valued credentials per market have verification notes | | ✓ | |
| Salary conversion: golden cases (period, basis, FX, tax model) produce expected comparable values | ✓ | | |
| Eligibility: golden profile × job cases give expected eligible/ineligible with reasons | ✓ | ✓ | |
| Source parsing: every source/alert parser listed for the market passes its golden dataset | ✓ | | |
| Strategy: channel weights sum to 1; volume range sane; onboarding steps exist | | | ✓ |

### 8a.2 Synthetic test profiles
A library of fictional, clearly synthetic profiles in `tests/synthetic/profiles/` covers
personas, fields, seniorities and countries. Each has expected outcomes (eligible job IDs,
ineligibility reasons, CV format, pay comparison) against the golden datasets. CI runs them
**end to end in dry-run**: discover from fixtures → normalize → match → documents → apply
dry-run → digest render. Initial set (grows with each market and role):

| ID | Profile | Exercises |
|---|---|---|
| `syn-01` | Mid-level Java backend engineer in Bengaluru → India + UAE | First configuration; INR vs AED comparison; UAE CV fields |
| `syn-02` | Registered nurse in Kerala → Saudi Arabia | Licence per market; sponsorship; monthly SAR; RTL documents |
| `syn-03` | Fresher in Pune → India (any IT/ops role) | Fresher persona; entry-level filters; campus channels |
| `syn-04` | Accountant in Manila → Canada | Credential recognition; CAD; mover persona |
| `syn-05` | Remote product designer in Lagos → remote global/EMEA | Remote-region eligibility; portfolio signals; USD/EUR pay |
| `syn-06` | Senior engineer in Berlin → Germany + remote EU | German CV norms; language requirement; EUR gross |
| `syn-07` | Returner (5-year caregiving gap), teacher in Manchester → UK | Returner persona; academic calendar; gap wording from user's own words |
| `syn-08` | Hospitality supervisor in Goa → Qatar | Monthly QAR package; sponsorship; trades/hospitality packs |
| `syn-09` | Executive (VP sales) in Singapore → Singapore + Australia | Executive persona; low volume; privacy defaults |
| `syn-10` | Electrician in Kochi → UAE | Trade certifications; practical tests |

All synthetic data is fictional; no real person's data is ever used.

### 8a.3 Golden datasets per market
`tests/golden/<market>/` holds sample postings (per source format) and job-alert emails with the
**expected normalized output** (JSON). Content is synthetic or anonymized and never copied
verbatim at length from real postings. Any change in normalized output fails CI until the
expected file is updated in the same PR, with the reason in the PR description.

### 8a.4 UI test matrix
Every screen is tested in every supported **language and direction**, with **currency and
date format** variants, at **phone (360 × 800) and desktop (1280 × 800, 1920 × 1080)** sizes,
in light and dark themes. Pull requests run a smoke matrix (one LTR and one RTL locale, phone and
desktop). The full matrix runs nightly and before releases. Checks: visual regression, axe
accessibility, no untranslated keys, no truncation or overflow, correct `dir`, mirrored icons,
locale formatting.

### 8a.5 Market rollout plan
Markets are enabled one at a time behind a feature flag (`market.<code>.enabled`). Priority
order (reviewed quarterly against user demand):

1. India + UAE (launch markets)
2. Saudi Arabia · 3. Qatar · 4. United Kingdom · 5. United States · 6. Canada · 7. Germany ·
8. Singapore · 9. Australia · 10. Remote (global and regional)

**Checklist per market (all required before the flag is turned on for users):**
- [ ] Market pack verified against official sources (`last_verified` set; links recorded)
- [ ] Sources connected and source policies reviewed (APIs, ATS catalogue, alert parsers)
- [ ] Pack conformance suite green
- [ ] Synthetic users for that market passing end to end
- [ ] Golden dataset for that market's sources committed and green
- [ ] Translations reviewed by a native speaker for the market's languages (including RTL review
      where relevant)
- [ ] UI matrix green for the market's locales and currency
- [ ] Owner sign-off recorded in `docs/decisions-log.md`

Roles follow the same pattern (`role.<code>.enabled`), with a checklist of pack verified,
credentials per enabled market, conformance green, synthetic profile passing.

## 9. Success metrics

### North star
**Interviews per week per active user** (median across active users; for user #1, the
absolute count). Interview = application entering `interview` state, by event time in the
user's time zone.

### Supporting
| Metric | Definition | Initial target |
|---|---|---|
| Callback rate | (human ack + assessment + interview) ÷ applied, 30 days | ≥ 10%; tracked per market, field, source |
| Applications/week | Submitted + one-tap confirmed | Within persona `daily_volume_range` |
| Time-to-first-response | Median days applied → first non-auto event | Tracked |
| Source / CV-variant conversion | Interviews ÷ applications | Ranked weekly |
| Ghosting rate | ghosted ÷ applied | Tracked |
| Activation (Stage 2+) | % signups who complete onboarding and see ≥ 5 eligible matches within 24 h | ≥ 60% |
| Retention (Stage 2+) | % active users week 4 | ≥ 40% |
| Time spent | Minutes/day (self-reported + session) | ≤ 20 |
| UX quality | Lighthouse perf/a11y/best practices; CLS | ≥ 90 each; CLS < 0.1 |
| **LLM cost per active user** | LLM tokens and cost attributed to the user per month, plus their share of system tokens (normalization, job embeddings) | **≤ 0.8 M generative tokens and ≤ US$0.20 LLM cost per MAU per month** at Stage 3 (estimate after tiering: ≈ 0.68 M and ≈ US$0.15; before: ≈ 3.9 M and ≈ US$0.80) (ADR-0023; re-check against current provider prices before each stage) |
| Tier 2 coverage | % of eventually-applied jobs that were in the user's LLM top N | ≥ 90% (validates that the cheap tiers don't hide good jobs) |

### Guardrails (must hold)
- **0** duplicate applications; **0** fabricated facts; **0** submissions while paused, lane
  disabled, over cap or below quality threshold; **0** automated actions on one-tap-only hosts.
- **0** cross-tenant data access (isolation tests in CI).
- Employer complaints: 0 tolerated without investigation; any confirmed abuse → suspension.
- Digest by 08:15 local on ≥ 99% of days; API availability ≥ 99.5%.
- LLM spend within per-user and deployment budgets.

## 10. Risks and mitigations

| # | Risk | L | I | Mitigation |
|---|---|---|---|---|
| R1 | Thin coverage in markets without public APIs (UAE first) | H | H | Alert emails as main source (Phase 2); curated employer catalogue per market; extension save-to-JobRadar; coverage per source and market monitored |
| R1a | Alert email formats change | M | H | Parser per sender + fixtures + `degraded` detection |
| R1b | Email access privacy and Google restricted-scope verification for public use | H | H | Narrow query, body discard, consent; forwarding-address inbox for the public stage (US-11.2) |
| R2 | Terms violations / account bans | M | H | Source policy registry; one-tap only where required; extension user-in-control; caps |
| R3 | LLM fabrication | M | Critical | Facts-only tailoring; claim-to-fact check; unknown question → ask user |
| R4 | Prompt injection via job text, emails, page content (extension) | M | H | Untrusted-data framing; schema validation; LLM never submits; extension never executes page-provided instructions |
| R5 | Wrong eligibility (visa, licence, nationality) | M | M | Rules + LLM with confidence; "unknown" shown, not silently passed; user feedback |
| R6 | Misleading pay comparison | M | M | Assumptions + dates shown; no estimating; per-market models tested |
| R7 | Duplicate or erroneous submissions | L | Critical | Idempotency, submit-time guards, dry-run default, proof, kill switch |
| R8 | LLM cost grows with users | H | H | Tiered matching (rules → shared embeddings → LLM top N, ADR-0023); small model for normalization/classification; caching; batching; per-user budgets |
| R8a | Embedding tier hides good jobs | M | M | Tier 2 coverage metric; "possible match" list with on-demand scoring; owner thumbs feed the eval set |
| R16 | A market or role ships with wrong facts or broken parsing | M | H | Conformance suite, golden datasets, synthetic users, native-speaker review, per-market flags (§8a) |
| R9 | Stale market/role facts across many packs | H | M | `last_verified` + warnings; pack owners/contributors; links to official sources |
| R10 | Personal data breach | L | Critical | Isolation + RLS, encryption at rest, no PII in logs, least-privilege tokens, threat model, pen-test before public |
| R11 | Product used to spam employers | M | H | §7.1 rules server-side, per-employer caps, cool-downs, suspension, audit, abuse contact |
| R12 | Scope creep from "product for everyone" | H | H | Stage gates; one user first; packs over code; phases in `CLAUDE.md` |
| R13 | Premium UI raises build cost | M | M | Design system first; shadcn/Radix primitives; visual regression prevents rework |
| R14 | Browser store review / extension permission concerns | M | M | Minimal per-host permissions, clear privacy disclosure, user-in-control |
| R15 | Legal exposure as a public product (DPDP, GDPR, terms) | M | H | Privacy policy, consent records, export/delete, grievance contact, legal review before Stage 3 |

## 11. Out of scope

- Billing and payments (plans only set limits until a later decision).
- Native mobile apps (PWA only).
- Employer-side features, recruiter CRM, job posting.
- Gig-marketplace bidding (Upwork/Fiverr proposals).
- Automated submission, autofill or scraping on hosts whose policy forbids it; CAPTCHA solving;
  anti-bot evasion.
- Immigration, visa, tax, licensing or legal advice; visa application processing.
- Sending messages to recruiters/employers on the user's behalf (drafts only; the user sends).
- AI mock interviews and video practice; calendar write access.

## 12. Decisions and open questions

### Resolved
- v0.2 review: FX manual dated rate (USD-peg derivation later); India new tax regime default;
  UAE CV field defaults; Naukrigulf via alerts/one-tap; Gmail alert ingestion in Phase 2;
  curated UAE company list (ADR-0008 … 0010).
- v0.3 review (2026-10-30): product for everyone (ADR-0013); web app + premium design system,
  Streamlit removed (ADR-0014, 0015); browser extension default, home runner optional
  (ADR-0016); auth and multi-tenancy (ADR-0017); privacy and consent (ADR-0018); quotas and
  anti-abuse (ADR-0019); i18n/RTL (ADR-0020); role taxonomy (ADR-0021); source policy registry
  (ADR-0022); import-linter approved (ADR-0012 accepted); seniority stays a profile setting.

- v0.4 review (2026-10-30): all four v0.3 calls approved; extension side panel with copy buttons
  on one-tap hosts (never reads, fills or clicks); tiered matching and cost target (ADR-0023);
  multi-market quality gates and rollout plan (ADR-0024); owner seniority `mid`.

### Open
1. Role taxonomy backbone licensing: ESCO (EU reuse terms) vs ISCO-08 groups only — check before
   Phase 3 (ADR-0021).
3. Inbound email provider for forwarding addresses (Phase 11).
4. Transactional email and web-push libraries/providers (dependency approval at Phase 4).
