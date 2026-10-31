# Decisions log

## 2026-10-30

Initial record of decisions previously agreed in chat. Their original decision dates are not
available in the repository.

- **Project name:** JobRadar (`jobradar`).
- **Architecture:** modular monolith, organized around the product domains and responsibilities
  defined in `CLAUDE.md`.
- **Logged-in portal execution:** use a home runner on the user's machine; portal logins and browser
  credentials remain local and cookies are never uploaded.
- **LinkedIn and Indeed applications:** LinkedIn Easy Apply and Indeed Apply are one-tap lanes only.
  The system prepares materials and links for the user; it does not automate submission.
- **Repository visibility:** the GitHub repository is intended to be private.
- **Project location:** project lives at `C:\dev\jobradar`, never in OneDrive. The OneDrive copy
  remains only as a retained backup and must not be used for ongoing work.
- **Target market and role:** India plus the United Arab Emirates (UAE), with Java Backend as the
  target role, as confirmed by the user on 2026-10-30.
- **Profile parsing:** declare PyYAML directly for YAML loading. The initial resume parser supports
  UTF-8 plain text only and extracts explicit labels rather than inferring profile facts.
- **PRD review (owner, 2026-10-30):**
  - FX: manual dated AED→INR rate in config for v1. Later automation derives AED→INR from
    USD→INR through the AED/USD peg (about 3.6725, held in config).
  - India in-hand estimates default to the new tax regime; old regime is a profile option.
  - UAE CV: photo, date of birth and marital status off by default with a per-application
    toggle; nationality, current location, visa status and notice period on by default.
  - Naukrigulf is a UAE channel through alert emails and one-tap links only; no scraping.
  - Read-only Gmail ingestion of job-alert emails (LinkedIn, Naukrigulf, Bayt, GulfTalent)
    moves into Phase 2 as the main UAE source. Inbox-based application tracking stays in Phase 6.
  - Phase 2 adds a curated list of UAE-hiring companies on Greenhouse, Lever, Ashby, Workable
    and SmartRecruiters, plus Workable and SmartRecruiters connectors.
- **Step 2 review (owner, 2026-10-30):** HLD approved with major changes; ADR-0011 and ADR-0012
  accepted; import-linter approved as a dev dependency. Seniority stays a profile setting until
  the owner confirms a value.
- **Scope change: a product for everyone (ADR-0013).** JobRadar serves any role, any country and
  any seniority, in tech and non-tech fields. User #1's profile (India + UAE, Java backend) is the
  first configuration, not the scope. Strategy: design for everyone, launch with one user, then
  friends (invite-only), then the public. Adding a country or role must need no core code changes.
  Amends ADR-0006.
- **Web app is the main product; premium UI stack (ADR-0014, ADR-0015).** React + TypeScript
  (Vite), Tailwind, shadcn/ui on Radix, Motion, TanStack Query, Lucide, Recharts, Storybook,
  Playwright visual regression, Lighthouse CI; installable mobile-first PWA. Streamlit is removed
  everywhere. Design system first, with tokens as the only source of visual values. Telegram,
  email and web push become optional notification channels.
- **Browser extension for logged-in portals (ADR-0016).** Runs in the user's own browser; the
  user reviews and clicks submit. No content scripts on one-tap-only hosts. The home runner
  becomes an optional mode. Amends ADR-0002.
- **Self-serve signup, roles and per-user isolation (ADR-0017).** Self-hosted auth (argon2id,
  Google OIDC, TOTP for admin/owner), server-side sessions, scoped client tokens, explicit
  `UserScope` plus Postgres row-level security.
- **Trust and legal (ADR-0018).** Explicit consent per data source, export and full deletion,
  aligned with the DPDP Act and GDPR; privacy policy and terms before Stage 2. Email access:
  Gmail API for Stages 1–2, per-user forwarding address as the public default.
- **Usage limits, budgets and anti-abuse (ADR-0019).** Plans as config, global ceilings, per-user
  LLM budgets, quality thresholds, per-employer caps, cool-downs and suspension; enforced
  server-side.
- **Multi-language including RTL (ADR-0020).** ICU messages, logical CSS properties, Inter plus
  Noto Sans Arabic.
- **Role taxonomy across all fields (ADR-0021).** Field → family → role on an ISCO-08 backbone
  (ESCO if licensing allows), with per-market credentials and hiring patterns in role packs.
- **Source policies (ADR-0022).** One registry decides the allowed access modes per host;
  unknown hosts default to one-tap only.
- **Phases revised (PRD v0.3).** Phase 4 becomes the web app foundation and design system;
  Phase 8 the browser extension (home runner optional); new Phase 10 (multi-user readiness,
  friends) and Phase 11 (public launch). `CLAUDE.md` is updated to match in Step 7.
- **v0.3 review (owner, 2026-10-30):** PRD v0.3 and HLD v0.2 approved, including the four calls
  (no page interaction on one-tap hosts, forwarding-address email default for the public stage,
  Recharts / Inter + Noto Sans Arabic / pnpm workspace / ISCO-08 backbone, auth and messaging
  libraries deferred to Phase 4).
- **Owner seniority:** `mid`. Local (git-ignored) `config/profile.yaml` sets `persona: mid` and
  `seniority: mid`; `packs/personas/mid.yaml` added.
- **Extension side panel on one-tap hosts:** the extension may show a side panel with prepared
  answers and copy buttons; it never reads, fills or clicks anything on LinkedIn, Indeed or Gulf
  board pages (ADR-0016 refined).
- **Tiered matching and cost target (ADR-0023):** rules → shared job embeddings → batched LLM
  scoring of each user's top N; small model for normalization and classification; aggressive
  caching. Target ≤ 0.8 M generative tokens and ≤ US$0.20 LLM cost per MAU per month at Stage 3.
  pgvector proposed; dependency approval pending.
- **Multi-market and multi-role testing (ADR-0024):** pack conformance suite, golden datasets per
  market, synthetic users end to end in CI with recorded LLM responses, UI locale/direction/
  viewport matrix, and per-market/per-role rollout flags with a checklist. Order after
  India + UAE: Saudi Arabia, Qatar, UK, US, Canada, Germany, Singapore, Australia, Remote.
- **Step 3 review (owner, 2026-10-30):** LLD approved.
  - `hired` and `declined` final states and the `assisted` lane (browser extension) approved.
  - Schedules (digest, follow-ups, ghosting, weekly report, re-plan) run in each user's time zone
    instead of fixed IST times.
  - New config files approved: `config/connectors.yaml`, `config/alert_senders.yaml`,
    `config/compensation/<market>/<date>.yaml`, `config/consents/`, `config/source_policies.yaml`.
  - Live auto-submit unlocks per user only after a recorded dry-run review.
  - pgvector approved; docker-compose uses the official `pgvector/pgvector:0.8.0-pg16` image (the
    local dev database was reindexed and its collation version refreshed after the image switch).
    Sign-in, email and push libraries remain deferred to Phase 4.
  - Schema is incremental: each phase's migration creates only the tables that phase needs
    (`docs/lld/database.md` §9).
- **Step 4 review (owner, 2026-10-30):** API contract approved.
  - Owner/admin TOTP ships with sign-in in Phase 4 (not Phase 10), because the admin console is
    internet-facing from Phase 7.
  - The ~30 response models designed in Step 4 are approved and recorded in the LLD of the
    owning module; the LLDs remain the single source of truth for models.
  - `docs/openapi.yaml` is the hand-maintained API contract. From Phase 4, CI compares it with
    FastAPI's generated schema for shipped phases. Contract changes need a PR that states the
    reason. The initial generator is archived at `scripts/archive/gen_openapi.py` and is not
    the source of truth.
  - New rule for `CLAUDE.md` §2 (applied in Step 7): nothing project-related may exist only in
    a session scratch folder; scripts, reports and generated artifacts that matter are saved in
    the repo, or discarded on purpose.
- **Step 5 review (owner, 2026-10-30):** coding standards and tooling approved.
  - `pytest-cov` approved; CI enforces ≥ 80 % branch coverage overall and on core, normalizer,
    matching, lifecycle and apply (PRODUCT_STANDARDS Q).
  - `pip-audit` and `openapi-spec-validator` run in CI through `uvx` (not project dependencies).
    `gitleaks/gitleaks-action` approved.
  - All GitHub Actions are pinned to full commit SHAs with a version comment; Dependabot updates
    GitHub Actions and Python (uv) dependencies weekly.
  - Existing commit history is not rewritten to match the conventional-commit rule.
  - **Process change:** commit and push at the end of every step from now on (Steps 1–5 committed
    as separate conventional commits on 2026-10-30).
- **Brand direction (owner, 2026-10-30, ADR-0025):** Direction A "Calm Compass" (teal, Inter +
  Noto Sans Arabic, radius 8/10/14 px, gentle motion), with Direction B's celebration animation
  used only for interviews and offers. `docs/design-system.md` and `docs/ux.md` written from it.
- **Step 6 review (owner, 2026-10-30):** design system and UX approved.
  - Swipe gestures on by default with a one-time hint and visible buttons. Swipe right = queue to
    apply with a 10-second undo (never an immediate final submit); swipe left = skip with undo.
  - Tier 1 possible matches appear only in Jobs (Possible tab), never on Today or in digests.
  - Privacy rule: no remote images in emails (coloured initials badges for companies). The web app
    and extension load images only from our own origin; company logos are fetched server-side and
    served through our caching proxy (`GET /companies/{company_id}/logo`, Phase 4). Contract change
    reason: this privacy rule. Adds access mode `logo_fetch` (ADR-0022 amendment) and
    `companies.logo_*` columns (Phase 4 expand).
- **Step 7 (2026-10-30):** `CLAUDE.md` rewritten to match the final PRD, HLD, phases, schedules
  and standards, including the per-phase workflow, the "nothing only in a scratch folder" rule and
  commit-and-push after every step. The documentation gate before Phase 2 is lifted.
- **Phase 2a (2026-10-30):** `SourcePolicy`, `AccessMode` and the policy registry live in
  `jobradar.core.source_policies`, not `connectors`: the pack schemas in `core` need `AccessMode`
  and `core` may not import a domain. Connectors re-exports the policy functions. Sensitive CV
  fields (photo, date of birth, marital status) are rejected as default-on by the market pack
  schema in every market. Source policies grant ATS boards `ats_feed` + `extension_assist` only;
  `server_apply` waits for a per-ATS terms review. Market and role packs keep
  `last_verified: null` until their facts are checked against official sources (they log a
  warning until then).
- **Phase 2c (2026-10-30):** the application never queries as its database login. Every
  transaction switches into a login-less role (`jobradar_app` or `jobradar_corpus`) with
  `SET LOCAL ROLE`, because superusers (the dev/CI login) bypass row-level security. The `jobs`
  table gets discovery columns in Phase 2 and normalized columns in Phase 3. Migrations contain no
  personal data: the owner account is created by a CLI command. Integration tests use
  testcontainers (works on Windows), with `JOBRADAR_TEST_DATABASE_URL` as the compose fallback.
- **Phase 2d (2026-10-30):** ATS connectors (Greenhouse, Lever, Ashby, Workable, SmartRecruiters)
  are entry-point plug-ins validated at startup against source policies and
  `config/connectors.yaml`. Response shapes were checked once against the live public APIs through
  `PoliteClient` (that probe also found and fixed a bug: query strings already in a URL were
  dropped); committed fixtures are synthetic. Health rule refined: drop and zero-job alerts apply
  only to sources averaging ≥ 5 jobs per run over the last 7 days, because quiet sources swing
  too much. Location
  aliases for dedupe live in `config/locations.yaml`. Known limits: SmartRecruiters descriptions
  are not fetched (one extra request per posting); Workable's posting fields follow its documented
  format until 2g verifies a live account with open jobs.
- **Phase 2e (2026-10-30):** Adzuna (India) and Remotive (remote) are query connectors planned
  from packs (country market × role aliases). Predicted salaries from Adzuna are never stored.
  Per-day request budgets from source policies are enforced from recorded runs. A live Remotive
  check (1 request) stored 12 real remote jobs with 0 invalid items. That run also showed httpx
  logging full request URLs at INFO; httpx/httpcore loggers are now held at WARNING so API keys in
  query strings never reach logs.
- **Adzuna (owner, 2026-10-30):** Adzuna is paid: the free "Pending Activation" plan allows 25
  test calls in total; full access is £8/month for 5,000 calls/month (500/day). The owner will
  not subscribe for now, so the Adzuna connector is **disabled in Stage 1**
  (`enabled: false` in `config/connectors.yaml`; discovery reports it as skipped). Revisit before
  Stages 2–3. **Stage 2 terms-review item:** the Adzuna app is registered for "Personal job
  search"; multi-user use needs a terms review (and likely a different plan) first.
- **India alert sources (owner, 2026-10-30):** because Adzuna was the main India aggregator, 2f
  adds job-alert email parsers for Naukri, LinkedIn India, Instahyre and Foundit alongside the UAE
  ones (LinkedIn, Naukrigulf, Bayt, GulfTalent). All are alert-email + one-tap sources.
- **Phase 2f-1 (2026-10-30):** HTML parser for alert emails: **BeautifulSoup4** on the stdlib
  `html.parser` backend (most widely used and tolerant of messy table-based email HTML; no
  compiled dependency; volume is low). Google OAuth uses **google-auth-oauthlib** (approved
  Google client libraries); Gmail REST calls go through `PoliteClient`. Alert parsers are one
  config-driven class (`config/alert_senders.yaml`); fixtures are synthetic until real alerts are
  available after the owner connects Gmail. Minimal `privacy` (consent per source, versioned
  consent texts in `config/consents/`) and `accounts` (owner bootstrap via the operator database
  path) slices added. `connectors.service` became a package so alert ingestion counts as the
  domain's service under the layering contract.
- **Phase 2f-2 (2026-10-30):** Gmail is called through `PoliteClient` (REST), not the Google API
  client library, so the same policy, timeout, retry and no-URL-logging rules apply; only the
  interactive consent uses `google-auth-oauthlib`. The Gmail refresh token is encrypted with
  AES-256-GCM (`cryptography`, already installed by `google-auth`; declared directly — owner
  confirmation requested). The OAuth client file stays outside the repository
  (`GOOGLE_OAUTH_CLIENT_FILE`). An inbox whose grant Google rejects becomes `reauth_required`.
- **cryptography (owner, 2026-10-31):** approved as a direct dependency (AES-256-GCM for stored
  OAuth refresh tokens).
- **Adzuna live check (owner, 2026-10-31):** skipped for now; no key is saved in `.env`. The
  connector stays disabled; the one-call verification runs if a key is added later.
- **Phase 2g — company catalogue (2026-10-31):**
  - ATS boards for candidate employers are found by **probing guessed slugs** on the five public
    ATS APIs (one polite request per guess, stopping at the first board with UAE jobs), because
    which ATS an employer uses is not published anywhere we may read. A guessed slug can belong
    to a different company with the same name, so probe output is a review list: only the
    owner's approval moves an entry into `config/companies.yaml`.
  - A board counts as "UAE-hiring" when it currently lists at least one job located in the UAE
    (normalizer location rules), not merely when the company has a UAE office.
  - `companies verify` treats a board checked in the last 24 h as cached (PRD US-2.7 AC2).
  - Alert employers become per-user suggestions merged by normalized name; accepting needs a
    board and at least one country; accepted companies go to the database catalogue and the CLI
    reminds the owner to add them to `config/companies.yaml`.
  - Candidate names and probe output are kept in `config/company_candidates/` (rule 12).
  - Bug fixed in `PoliteClient`'s token bucket: float rounding in the refill could leave
    0.999… tokens and a wait too small to move the clock, which spun forever with a fake clock
    (and caused needless tiny sleeps with the real one). Regression test added.
- **UAE catalogue approved (owner, 2026-10-31):** all 36 proposed companies, including the seven
  with a single UAE posting, because discovery and `companies verify` re-check every board.
- **Excluded industries (owner, 2026-10-31):** users can exclude industries from matching
  (profile `excluded_industries`; empty for the owner). Codes come from a fixed vocabulary,
  `config/industries.yaml` (crypto, gambling, real-money gaming, tobacco, alcohol, weapons and
  defence, fossil fuels, adult content, high-cost lending); unknown codes are rejected on load.
  Only **explicit** company tags count (`industries` in `config/companies.yaml`): an untagged
  employer is never guessed into an industry, so alert-only employers are not excluded until
  tagged. The ten crypto companies in the UAE catalogue are tagged `crypto`. Enforcement is the
  Phase 3 eligibility rule `excluded_industries` (reason `eligibility.excluded_industry`); the
  pure check `core.industries.excluded_industries` exists now, and the Phase 3 migration adds
  `profiles.excluded_industries` and `companies.industries`.
- **Workday and unknown hiring systems (owner, 2026-10-31):** employers on Workday or any system
  outside the five supported ATSs stay **one-tap via alert emails**: no connector, probe or
  suggestion reads their boards (`*.myworkdayjobs.com` and unknown hosts allow `one_tap` only;
  `ATS_ORDER` has no Workday). Their jobs reach JobRadar through job-alert emails, and the user
  applies on the employer's site. Pinned by `tests/unit/connectors/test_one_tap_systems.py`.
- **Real alert samples (owner, 2026-10-31):** parser fixes use real alerts only through
  anonymized fixtures. The owner downloads one alert as `.eml` into `%USERPROFILE%\.jobradar\samples\`
  (outside the repo); `scripts/archive/anonymize_alert_email.py` rebuilds it with the same HTML
  layout and fake text, IDs, links and headers, checks that no original detail remains, and the
  original is deleted. Email contents are never shown in chat or logs.
