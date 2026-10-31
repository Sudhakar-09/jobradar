# ADR-0017: Auth, sessions, scoped tokens and tenant isolation

- **Status:** Accepted
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "Self-serve signup, roles and per-user isolation"
- **Related:** PRD v0.3 US-4.2, US-10.1, US-10.4; PRODUCT_STANDARDS A; `docs/architecture.md` §4–§5

## Context
Self-serve signup, multiple clients (web, extension, Telegram, runner) and sensitive personal
data mean one bug must not expose one user's data to another. Roles `user`, `admin` and `owner`
are required.

## Decision
- **Self-hosted auth in the API:** email + password (argon2id) and Google sign-in (OIDC); email
  verification; password reset; TOTP required for `admin`/`owner`. Signup mode flag:
  `closed` → `invite` → `open`.
- **Web sessions:** server-side, hashed session IDs, HttpOnly + Secure + SameSite=Lax cookie,
  rotation on login and privilege change, CSRF double-submit header.
- **Client tokens:** hashed, scoped, expiring, revocable tokens per client type (extension,
  Telegram link, runner, admin API).
- **Isolation, layer 1:** a `UserScope` is passed explicitly from entry point → service →
  repository. Repositories require it, and there is no ambient "current user".
- **Isolation, layer 2 (defence in depth):** **Postgres row-level security** on every user-owned
  table, using `current_setting('app.user_id')` set with `SET LOCAL` per transaction. The app
  role cannot bypass RLS. Shared-corpus workers use a role without grants on user tables.
- **Admin:** operational data only. User content needs a time-limited support grant from the
  user, which is audit-logged.
- **Tests:** a generated cross-tenant suite over every endpoint and task, plus RLS SQL tests.

## Consequences
- Positive: two independent isolation layers, and least-privilege clients.
- Negative: RLS adds migration discipline (policies per table) and test fixtures that set
  `app.user_id`. Auth libraries need approval when Phase 4 starts.

## Alternatives considered
- **External identity provider (Auth0, Clerk, Cognito):** faster, but adds vendor cost and lock-in
  and sends personal data to a third party. Can be revisited if enterprise SSO is ever needed.
- **Service-layer scoping only:** one missed filter leaks data. Rejected.
