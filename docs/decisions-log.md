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
- **Germany added as a market (owner, 2026-10-31):** the owner's LinkedIn alerts kept returning
  German jobs, so Germany becomes a full market for user #1 (with India and the UAE), moved to the
  top of the rollout list. Pack `packs/markets/germany.yaml`: EUR, annual gross, `germany_gross`
  compensation model (Phase 3), EU Blue Card / skilled worker / Opportunity Card routes, anabin
  degree recognition, CV photo and nationality off by default. Sources: company ATS boards,
  LinkedIn, StepStone, XING, Indeed — the job boards are alert email + one-tap only (new
  StepStone and XING source policies). StepStone and XING alert parsers are added once real
  alerts exist (anonymized fixture rule). German cities added to `config/locations.yaml`;
  Adzuna maps `germany` → `de` for when it is enabled. Germany joins the 2h conformance suite.
  A Germany company list is built like the UAE and India ones.
- **Language filter (owner, 2026-10-31):** the owner works in English only (profile
  `languages: [en]`, ISO 639-1 codes). Postings that require German — by requirement phrases
  such as "fluent German" / "sehr gute Deutschkenntnisse", or by being written in German — are
  ineligible (`language` rule, reason `eligibility.language_missing`); "German is a plus" never
  blocks. Postings written in one of the user's languages rank higher (`language_fit` 1.0 vs 0.9
  for unknown). Phrases and stopwords are config (`config/language_requirements.yaml`); the pure
  detector `normalizer.language_signals` exists now, the eligibility rule lands in Phase 3.
- **EU Blue Card thresholds as dated data (owner, 2026-10-31):** stored in
  `config/market_data/germany/eu_blue_card.yaml` (2025: €48,300 / €43,759.80; 2026: €50,700 /
  €45,934.20 standard / reduced, gross annual base salary), verified 2026-10-31 against public
  sources; the experience-based IT threshold is left out because sources disagree. New
  `core.dated_data` gives effective-dated lookups with stale warnings (> 90 days unverified, or
  past the newest entry) and no extrapolation; Phase 3 tax tables will use it too. Matching gets a
  `visa_salary` warning rule (Phase 3).
- **Conformance v1 and rollout gate (2026-10-31, US-2.9):** the suite checks what Phase 2 can
  answer from configuration (provenance, visa routes and dated thresholds, gazetteer, language
  rules, alert parsers per source, catalogue, golden datasets); later checks arrive with their
  modules. Golden datasets for India, UAE and Germany (synthetic, incl. German language cases).
  The minimal `admin` domain (flag service) refuses to enable a market or role that fails, and
  audits every change; it runs the suite live in Stage 1 instead of reading a CI artifact.
  Arabic language rules added for the UAE's `ar-AE` locale; German title words decide the
  language of title-only alert jobs. Current status: all markets fail `provenance` until their
  packs are verified against official sources; India and Germany also lack approved company
  lists and an Indeed parser; Germany lacks StepStone and XING parsers.
- **UAE pack verified (2026-10-31):** 25 values recorded in `packs/verification/uae.yaml` —
  8 verified on official sources (u.ae, MoHRE: no personal income tax, AED peg 3.6725, work
  permit + residence visa route, Emiratisation quotas, notice 30–90 days under Art. 43 of
  Decree-Law 33/2021, basic vs package for gratuity, mandatory employer health insurance),
  15 secondary (CV norms, job boards, monthly quoting, language), 2 unverified awaiting the
  owner (education/annual-flight allowances being common; no public sponsor register).
  Pack corrected: visa route official URL → u.ae work-visa page; summary names MoHRE / ICP /
  GDRFA, free zones, DIFC/ADGM and Green/Golden visas; concrete notice period; gratuity on basic
  wage; Arabic contracts note. Photo stays off by default although customary (owner decision).
  mohre.gov.ae and centralbank.ae blocked direct fetches; those facts rest on u.ae pages and
  search excerpts of the official pages.
- **India pack verified (2026-10-31):** 25 values in `packs/verification/india.yaml` — 8 on
  official sources (incometax.gov.in: progressive slabs, new regime default under s.115BAC and
  s.202 of the Income-tax Act 2025 from tax year 2026-27 per the Finance Bill 2026; EPFO: 12% PF,
  Rs 15,000 ceiling; Ministry of Labour: Labour Codes 50% wage rule; Maharashtra PT schedule and
  Art. 276 cap), 14 secondary (CTC conventions, CV norms, notice periods, job boards), 3
  unverified for the owner (states without professional tax; no visa routes or credential
  recognition listed, since the pack targets Indian citizens). Pack corrected: concrete PF, PT
  and regime notes; notice-period norm with IT figures; photo scoped to IT/private sector.
- **Germany pack verified (2026-10-31):** 32 values in `packs/verification/germany.yaml` — 26
  official (Bundesanzeiger BMI notices for all Blue Card figures; AufenthG §§ 18b, 18g, 20a;
  BGB § 622; EStG §§ 32a, 38b; SolZG; DRV; Federal Employment Agency CV and language guidance;
  anabin), 5 secondary, 1 unverified for the owner (en-DE locale, checked in Phase 4). Two
  statements were wrong and are corrected: skilled worker permits no longer require the job to
  match the qualification (§ 18b, since 2023); statutory notice grows with tenure only for the
  employer (§ 622 BGB). The Blue Card table now cites the official notices and stores the
  § 18g(2) IT-without-degree minimum (equal to the reduced value). Blue Card and Opportunity Card
  links point to the official Make it in Germany PDFs (the HTML pages sit behind a bot wall).
- **Verification review (owner, 2026-10-31):** (1) UAE allowances reworded neutrally — offers
  may include housing, transport, education and flights; compare the full package — no
  prevalence claim, accepted without source; (2) UAE: "no public sponsor register found as of
  2026-10-31" accepted; (3) India professional tax: state examples removed, only "varies by
  state, at most ₹2,500 a year" kept, per-state data later from state sources; (4)(5) India visa
  routes and foreign degree equivalence accepted for Stage 1 (Indian citizens) and recorded as
  gaps in the pack (`known_gaps`, new optional market-pack field) and `docs/markets/india.md`
  (rollout checklist): both must be added and verified before India is enabled for non-Indian
  users; (6) Germany `en-DE` accepted, verified in Phase 4. Decisions are stored as
  `owner_accepted_on: 2026-10-31` in `packs/verification/*.yaml`. Result: the UAE pack passes
  conformance.
- **Role and persona packs verified (2026-10-31):** `java_backend` (17 values) against ESCO
  (European Commission), ISCO-08 via ESCO, Amazon's published SDE interview process, Ashby
  recruiting data and a new corpus analysis of 524 Java postings
  (`docs/research/java-backend-corpus-2026-10-31.md`, aggregates only); `mid` persona (11
  values), mostly product settings. New verification status `editorial` (our own judgement;
  blocks conformance until the owner accepts) and `evidence` (repo path of our own analysis, in
  place of a URL). ESCO reuse is allowed with attribution ("uses the ESCO classification of the
  European Commission", modified labels marked); ISCO-08 is stored as code and short title only
  (ILO copyright for pre-2023 material). Findings for the owner: ESCO has no backend / platform /
  full-stack occupation; real postings are titled "Software Engineer" and are mostly senior; the
  role pack has no seniority signals; the persona's follow-up schedule ([7, 14]) conflicts with
  its tip ("follow up once"); only 2 UAE-located Java postings across the 36 UAE catalogue
  companies.
- **Role/persona review (owner, 2026-10-31):** (1) all editorial values in `java_backend` and
  `mid` accepted as starting defaults (`owner_accepted_on`).
- **Follow-ups (owner, 2026-10-31):** one follow-up, 7–10 days after applying, then the ghosting
  rules apply. Persona `mid` `followup_days: [7]` and its tip now agree; lifecycle LLD updated.
- **Generic titles and seniority (owner, 2026-10-31):** (3) "Software Engineer", "Backend
  Engineer", "Software Developer", "SDE" (and "Software Development Engineer") count for
  `java_backend` only when the description shows Java plus Spring/JVM work
  (`conditional_title_aliases`, "requires description match", applied by Phase 3 matching).
  (4) Role packs gain `seniority_signals`: for a `mid` profile Staff/Principal/Architect/Director
  are ineligible, Senior/Lead an eligible stretch with a score penalty, plain/II/mid titles the
  target; I placed "III" under senior and "Head of"/"VP"/"CTO" under executive (for the owner to
  confirm). Year ranges per level wait for the owner's years of experience. Both share the role
  schema change, so they are one commit.
- **UAE sources (owner, 2026-10-31):** job-alert emails remain the primary UAE source; recorded in
  the UAE pack's new optional `source_notes` field. A third UAE company round (banks, telecoms,
  airlines, government-linked companies, IT services) is being probed and their hiring systems
  identified from web-search results (no scraping of their sites).
- **Seniority years (owner, 2026-10-31):** owner has 3.5 years (profile `years_exp: 3.5`);
  `java_backend` year ranges junior 0–2, mid 2–5, senior 5–8, staff 8–15, executive 10+. A
  posting's minimum years map to a level ("3+" mid target, "5+" senior stretch, "8+" staff
  ineligible); the higher of title level and years level counts. Confirmed: "III" = senior
  (stretch); "Head of", "VP", "CTO" = executive (ineligible).
