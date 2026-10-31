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
