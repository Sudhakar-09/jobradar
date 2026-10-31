# JobRadar — API contract (v1)

| | |
|---|---|
| Status | Draft for owner review |
| Version | 0.1 (2026-10-30) |
| Machine-readable spec | [`docs/openapi.yaml`](openapi.yaml) (OpenAPI 3.1) — the source for the generated TypeScript client (`frontend/packages/api-client`) and contract tests |
| Inputs | `docs/architecture.md` §3–§9, `docs/lld/*`, `docs/lld/README.md` (canonical identifiers, traceability) |

The API is the **only** way any client (web app, extension, Telegram bot, runner, admin console)
reads or changes data. Routers are thin: they authenticate, validate, build a `UserScope`, call
one service function and map the result or exception to HTTP. They contain no business logic.

---

## 1. Base URL, versioning and clients

- Base path: **`/api/v1`**, served on the same origin as the web app (no CORS for the web app).
- Path groups by client:

| Prefix | Client | Auth |
|---|---|---|
| `/api/v1/...` | Web app; Telegram bot on the subset of operations that list a `telegram` scope | Session cookie + CSRF header; or the user's Telegram token |
| `/api/v1/ext/...` | Browser extension | `Authorization: Bearer <extension token>` |
| `/api/v1/runner/...` | Optional home runner | `Authorization: Bearer <runner token>` |
| `/api/v1/admin/...` | Admin console (web, `admin`/`owner` role, MFA-verified session) | Session cookie + CSRF + role |
| `/api/v1/actions/...` | Signed action links from notifications (email, push, Telegram) | Signed short-lived action token |
| `/health`, `/ready` | Probes (unversioned) | None |

- **Compatibility within v1:** additive changes only (new endpoints, new optional fields, new enum
  values that clients must treat as unknown-safe). Removing or renaming a field, changing a type,
  or tightening validation requires `/api/v2`.
- **Client versions:** every client sends `X-Client-Version: <app>@<semver>` (e.g.
  `extension@1.4.0`). Below the configured minimum the API returns **`426 Upgrade Required`** with
  problem type `client_outdated`. The API supports the current and previous (N-1) client releases.
- **Deprecation:** deprecated operations return `Deprecation` and `Sunset` headers and are marked
  `deprecated: true` in the OpenAPI spec for at least one client release before removal in v2.

## 2. Authentication and authorization

| Mechanism | Details |
|---|---|
| **Web session** | `jr_session` cookie: HttpOnly, Secure, SameSite=Lax, Path=/. Server-side session (ADR-0017). State-changing requests (`POST`, `PUT`, `PATCH`, `DELETE`) must send `X-CSRF-Token` equal to the `jr_csrf` cookie (double-submit). |
| **MFA** | `admin`/`owner` sessions are limited to `/api/v1/auth/mfa/*` until TOTP is verified (`sessions.mfa_verified_at`). |
| **Client tokens** | `Authorization: Bearer jr_<kind>_<random>`; stored hashed; carry `scopes` (and `hosts` for the extension). Each operation in the spec lists required scopes under `x-scopes` (scope names: `docs/lld/accounts.md`). |
| **Telegram bot** | The bot holds no master key. Linking (`POST /notify/telegram/link`) issues a **per-user** `telegram` client token, stored encrypted by the bot and keyed by chat ID. The bot calls the normal endpoints with that token, so every bot action is limited to that user and those scopes. Unlinking or revoking the token cuts the bot off for that user immediately. |
| **Action tokens** | Signed (HMAC, key ID in token), single purpose (one action on one target), expire in 72 h, single use where the action is not idempotent. Sent in the `X-Action-Token` header (or the `/actions` request body), never in a URL query, so they stay out of logs. |
| **Bot service credential** | Used **only** by `POST /notify/telegram/link`, so the bot can exchange a user's one-time link code for that user's Telegram token (`botServiceToken` in the spec). It grants no access to any user's data by itself. |
| **Roles** | `user`, `admin`, `owner`. Admin operations list `x-roles` in the spec. Admins never receive user content without an active support grant (`x-support-grant: required`). |

**Tenant rule:** a resource that exists but belongs to another user returns **`404`**, never `403`,
so existence is not leaked. `403` is used only for missing scopes/roles on the caller's own data.

## 3. Requests and responses

- JSON only (`application/json; charset=utf-8`), except file upload (`multipart/form-data`) and file
  download (signed redirect).
- **Field naming:** `snake_case` in JSON (matches Pydantic models; the TS client maps types as-is).
- **IDs:** UUIDv7 strings. **Timestamps:** RFC 3339 UTC (`2026-10-30T08:00:00Z`). **Dates:**
  `YYYY-MM-DD`. Local-time fields are labelled `*_local` and accompanied by the user's IANA time zone.
- **Money:** `{ "amount": "18000.00", "currency": "AED", "period": "month" }` — `amount` is a
  decimal **string** (no floats).
- **Localization:** the API returns **message keys + params**, not translated text, for all
  system-generated messages (eligibility reasons, guard failures, notifications), e.g.
  `{ "key": "eligibility.visa_required", "params": { "country": "AE" } }`. The client renders with
  ICU in the user's locale. Free text coming from the LLM (rationale) or users is returned as-is,
  marked `untrusted: true` where it originates from third-party content, and must be rendered as text
  (never HTML).
- **Partial responses:** none in v1; responses are full resources or documented summaries.

## 4. Errors (RFC 9457 Problem Details)

Every error response is `application/problem+json`:

```json
{
  "type": "https://jobradar.app/problems/guard_failed",
  "title": "Action blocked by a safety rule",
  "status": 409,
  "code": "guard_failed",
  "detail_key": "guard.cap_reached",
  "params": { "metric": "applications.auto", "resets_at": "2026-10-31T00:00:00+05:30" },
  "correlation_id": "0192f1d2-…",
  "errors": []
}
```

| HTTP | `code` | Raised from (core/errors.py) | Notes |
|---|---|---|---|
| 400 | `bad_request` | malformed JSON, unknown query parameter | |
| 401 | `unauthenticated` | missing/expired session or token | |
| 403 | `forbidden` | `PermissionDeniedError` (scope/role) | |
| 403 | `csrf_failed` | CSRF check | |
| 403 | `mfa_required` | admin/owner without MFA | |
| 404 | `not_found` | `NotFoundError` (incl. other tenants' resources) | |
| 409 | `conflict` | `ConflictError` (duplicate, unique violation) | |
| 409 | `invalid_transition` | `InvalidTransitionError` | `params.from`, `params.to` |
| 409 | `concurrency_conflict` | `ConcurrencyConflictError` | client refetches |
| 409 | `guard_failed` | `GuardFailedError` | `detail_key` = guard code key |
| 412 | `precondition_failed` | `If-Match` ETag mismatch | |
| 422 | `validation_failed` | `ValidationFailedError` / Pydantic | `errors[]` = `{ "field": "salary.min", "key": "validation.min", "params": {} }` |
| 426 | `client_outdated` | client version below minimum | |
| 428 | `consent_required` | `ConsentRequiredError` | `params.source` |
| 429 | `rate_limited` / `quota_exceeded` / `budget_exceeded` | rate limiter / `QuotaExceededError` / `BudgetExceededError` | `Retry-After` header; `params.metric`, `params.resets_at` |
| 502 | `upstream_error` | `ExternalServiceError` (non-retryable) | |
| 503 | `upstream_unavailable` / `paused` | retryable external failure / maintenance | `Retry-After` |
| 500 | `internal_error` | anything unhandled | no internals in the body; correlation ID only |

## 5. Pagination, filtering, sorting

- **Cursor pagination** on all list endpoints: `?limit=` (default 25, max 100) and `?cursor=`
  (opaque). Response envelope:
  ```json
  { "items": [ … ], "next_cursor": "eyJ…", "has_more": true }
  ```
  No total counts on large collections (use dedicated `/counts` or summary endpoints).
- **Filters** are explicit query parameters documented per endpoint (e.g. `state=interview`,
  `market=uae`, `min_fit=70`, `q=` for search). Unknown parameters → `400`.
- **Sorting:** `?sort=field` or `?sort=-field` from a per-endpoint allow-list.

## 6. Concurrency, idempotency and optimistic updates

- **ETags:** single-resource `GET` returns `ETag`; `PATCH`/`PUT` accept `If-Match`. A mismatch returns
  `412`. The web app uses this for inline editing.
- **State transitions** accept `expected_from` in the body (state-machine.md §6) so drag and drop can
  roll back an optimistic move on `409 concurrency_conflict`.
- **Idempotency keys:** every non-idempotent `POST` that creates something or triggers work accepts
  `Idempotency-Key: <uuid>`; the API stores the first response for 24 h per (user, key, route) and
  replays it. Required (`x-idempotency: required`) on: apply/queue actions, "I applied"
  confirmations, extension proof uploads, runner result reports, exports, deletion requests.
- **Undo:** destructive user actions return `undo_token` and `undo_expires_at` (10 s); undo is
  `POST …/undo` with the token (state-machine.md §6).

## 7. Rate limits and quotas

- Per-IP and per-user token buckets in Redis. Response headers on every request:
  `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset` (IETF draft fields).
- Default limits (config, not code): authenticated web 600 req/min/user; auth endpoints 10 req/min/IP
  and 5 failed logins per account per 15 min; extension 300 req/min/token; runner 60 req/min/token;
  bot 30 msg/s global (Telegram limit) handled in the notify queue, not here.
- **Product quotas** (applications, documents, LLM budget) are separate from rate limits and return
  `429 quota_exceeded` / `budget_exceeded` with the metric and reset time. Usage is visible at
  `GET /api/v1/me/usage`.

## 8. Security headers and transport

Set by Caddy and the API: HTTPS only (HSTS), `Content-Security-Policy` (self + API; `img-src 'self' data:` so no third-party images; no inline
scripts), `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`,
`Permissions-Policy` minimal, `Cache-Control: no-store` on all `/api` responses except signed file
redirects. Request bodies are capped (1 MB JSON; 10 MB uploads, resumes only). Every request gets
`X-Correlation-ID` (accepted from the client if a valid UUID, otherwise generated) echoed in the
response and in problem bodies.

## 9. Endpoint catalogue

All paths are relative to `/api/v1` unless shown otherwise. **Phase** is when the endpoint first
ships; it matches the tables available in `docs/lld/database.md` §9. Nothing is built before its
phase.

**Auth key:** **P** public · **S** web session (+ CSRF on writes) · **S+MFA** admin/owner session
with TOTP · **T:**`scope` user's Telegram token · **E:**`scope` extension token · **R:**`scope` runner
token · **A:**`scope` admin API token · **K** signed action token · **W** webhook signature.

### 9.1 Health (unversioned)
| Method | Path | Purpose | Auth | Story | Phase |
|---|---|---|---|---|---|
| GET | `/health` | Process alive | P | US-0.1 | 0 ✅ |
| GET | `/ready` | DB, Redis, queue reachable | P | US-0.1 | 0 ✅ |

### 9.2 Auth and account (`accounts`)
| Method | Path | Purpose | Auth | Story | Phase |
|---|---|---|---|---|---|
| POST | `/auth/signup` | Create account (mode `closed`/`invite`/`open`; invite code when `invite`) | P (rate-limited) | US-10.1 | 10 |
| POST | `/auth/login` | Email + password → session (+ MFA step for admin/owner) | P (rate-limited) | US-4.2 | 4 |
| POST | `/auth/google` | Google OIDC callback → session | P | US-4.2 | 4 |
| POST | `/auth/totp` | Verify TOTP; marks session MFA-verified | S (pre-MFA) | US-10.1 | 4 (owner) |
| POST | `/auth/totp/enroll` | Start TOTP enrolment (secret + otpauth URI) | S | US-10.1 | 4 |
| POST | `/auth/totp/confirm` | Confirm enrolment with a code | S | US-10.1 | 4 |
| POST | `/auth/logout` | End this session | S | US-4.2 | 4 |
| POST | `/auth/logout-everywhere` | Revoke all sessions and rotate tokens | S | US-4.2 | 4 |
| POST | `/auth/verify-email` | Consume email verification code | P (code) | US-10.1 | 10 |
| POST | `/auth/password-reset/request` | Send reset email (always 202) | P (rate-limited) | US-10.1 | 10 |
| POST | `/auth/password-reset/complete` | Set new password with code | P (code) | US-10.1 | 10 |
| POST | `/auth/pair/start` | Create extension pairing code | S | US-8.3 | 8 |
| POST | `/auth/pair/exchange` | Exchange pairing code → extension token | P (code) | US-8.3 | 8 |
| GET | `/me` | Current user, role, locale, time zone, preferences | S | US-4.2 | 4 |
| PATCH | `/me` | Update locale, time zone, comparison currency, preferences | S | US-4.2 | 4 |
| GET | `/tokens` | List client tokens (no secrets) | S | US-10.4 | 4 |
| POST | `/tokens` | Create runner/admin API token (shown once) | S | US-8.1 | 8 |
| DELETE | `/tokens/{token_id}` | Revoke a token | S | US-10.4 | 4 |
| POST | `/support-grants` | Grant time-limited support access (≤ 72 h) | S | US-10.8 | 10 |
| DELETE | `/support-grants/{grant_id}` | Revoke support access | S | US-10.8 | 10 |

### 9.3 Controls, status and usage
| Method | Path | Purpose | Auth | Story | Phase |
|---|---|---|---|---|---|
| GET | `/me/status` | Pause state, lanes, today's counts, open questions | S, T:`read:summary` | US-4.5 | 4 |
| POST | `/control/pause` | Pause all apply activity for this user (owner: `scope=global` sets `PAUSE_ALL`) | S, T:`control:pause` | US-4.5 | 4 |
| POST | `/control/resume` | Resume | S, T:`control:pause` | US-4.5 | 4 |
| PATCH | `/flags/{key}` | Set a user-scoped flag (lane toggles etc.) | S, T:`control:user_flags` | US-4.6 | 4 |
| GET | `/me/usage` | Usage meters vs plan limits and reset times | S | US-10.5 | 3 (LLM budget), 10 (full) |
| POST | `/me/dry-run-review` | Record the dry-run review that unlocks live auto-submit | S | US-6.1 | 6 |
| GET | `/plans` | Available plans and limits | S | US-10.5 | 10 |

### 9.4 Packs and legal (read-only)
| Method | Path | Purpose | Auth | Story | Phase |
|---|---|---|---|---|---|
| GET | `/packs/markets` | Enabled market packs (summaries for onboarding) | S | US-1.2, US-10.2 | 4 |
| GET | `/packs/roles` | Enabled role packs; `?q=` searches title aliases | S | US-1.2, US-10.2 | 4 |
| GET | `/packs/personas` | Persona packs | S | US-10.2 | 4 |
| GET | `/legal/{doc}` | Privacy policy / terms / consent texts (`?version=`) | P | US-11.1 | 10 |

### 9.5 Profile, variants, answers, onboarding (`profile`)
| Method | Path | Purpose | Auth | Story | Phase |
|---|---|---|---|---|---|
| GET | `/profile` | Current profile (ETag) | S | US-1.1 | 4 |
| PATCH | `/profile` | Update fields (If-Match); bumps profile version | S | US-1.1 | 4 |
| POST | `/profile/resume` | Upload PDF/DOCX → draft with source spans (async; returns draft ID) | S | US-1.4 | 4 |
| POST | `/profile/resume/apply` | Apply confirmed draft fields to the profile | S | US-1.4 | 4 |
| GET | `/onboarding/status` | Wizard progress by persona | S | US-10.2 | 10 |
| GET | `/resume-variants` | List variants | S | US-5.1 | 5 |
| POST | `/resume-variants` | Create variant (market format × role × locale) | S | US-5.1 | 5 |
| PATCH | `/resume-variants/{variant_id}` | Edit content / default field toggles | S | US-5.1 | 5 |
| GET | `/answers` | Answer bank (`?q=`, `?scope=`) | S | US-1.3 | 5 |
| POST | `/answers` | Add answer | S | US-1.3 | 5 |
| PATCH | `/answers/{answer_id}` | Edit answer | S | US-1.3 | 5 |
| DELETE | `/answers/{answer_id}` | Delete answer | S | US-1.3 | 5 |

### 9.6 Inboxes, companies, consents (`connectors`, `privacy`)
| Method | Path | Purpose | Auth | Story | Phase |
|---|---|---|---|---|---|
| GET | `/consents` | Active and past consents | S | US-10.3 | 4 |
| POST | `/consents` | Grant consent for a source (`source`, `text_version`) | S, T:`actions:confirm_link` (Telegram only) | US-10.3 | 4 |
| DELETE | `/consents/{source}` | Revoke; takes effect immediately | S | US-10.3 | 4 |
| POST | `/inboxes/gmail/connect` | Start Gmail OAuth (read-only); requires consent `gmail_alerts` | S | US-2.5 | 4 |
| POST | `/inboxes/forwarding` | Create forwarding-address inbox | S | US-11.2 | 11 |
| GET | `/inboxes` | Connected inboxes and sync status | S | US-2.5 | 4 |
| DELETE | `/inboxes/{inbox_id}` | Disconnect inbox (revokes token) | S | US-2.5 | 4 |
| GET | `/companies/suggestions` | Employers seen in alerts, pending review | S | US-2.7 | 4 |
| POST | `/companies/suggestions/{suggestion_id}/decision` | Accept / reject suggestion | S | US-2.7 | 4 |
| GET | `/companies/{company_id}/logo` | Cached company logo via our proxy (image; 404 → client shows initials badge) | S, E:`ext:read_profile_view` | US-4.3 | 4 |
| POST | `/inbound/mail` | Inbound mail webhook (forwarding inboxes) | W | US-11.2 | 11 |

> In Phases 2–3 (before the web app), the Gmail connection and consent are done by the owner
> through the CLI (`jobradar inbox connect`), which calls the same services.

### 9.7 Matches and jobs (`matching`, `normalizer`)
| Method | Path | Purpose | Auth | Story | Phase |
|---|---|---|---|---|---|
| GET | `/matches` | Ranked eligible matches (`?market`, `?min_fit`, `?q`, `?since`, cursor) | S | US-3.4, US-4.3 | 4 |
| GET | `/matches/possible` | Tier 1 "possible matches" below the LLM cut | S | US-3.7 | 4 |
| GET | `/jobs/{job_id}` | Job detail + this user's score, eligibility reasons, pay comparison | S | US-4.3, US-3.5 | 4 |
| GET | `/jobs/{job_id}/explain` | Full score breakdown and rank components | S | US-3.3 | 4 |
| POST | `/jobs/{job_id}/score` | On-demand Tier 2 score (budget-counted) | S | US-3.7 | 4 |
| PUT | `/jobs/{job_id}/feedback` | Thumbs up/down with reason | S | US-3.3 | 4 |
| POST | `/jobs/{job_id}/apply` | Apply action: create/queue application (lane per source policy) | S, T:`actions:apply_skip_save`, K | US-4.3 | 4 (queue), 5 (prepare) |
| POST | `/jobs/{job_id}/skip` | Skip (undo token returned) | S, T:`actions:apply_skip_save`, K | US-4.3 | 4 |
| POST | `/jobs/{job_id}/save` | Save for later | S, T:`actions:apply_skip_save`, K | US-4.3 | 4 |

### 9.8 Applications, questions, documents (`lifecycle`, `apply`, `documents`)
| Method | Path | Purpose | Auth | Story | Phase |
|---|---|---|---|---|---|
| GET | `/applications` | Pipeline list (`?state`, `?lane`, `?saved`, `?q`, cursor) | S | US-6.5 | 4 |
| GET | `/applications/{application_id}` | Application detail | S | US-6.5 | 4 |
| GET | `/applications/{application_id}/history` | Event timeline | S | US-6.5 | 4 |
| POST | `/applications/{application_id}/transition` | User transition (`to_state`, `expected_from`) — drag and drop | S | US-6.5 | 4 |
| POST | `/events/{event_id}/undo` | Undo a skip/withdraw within 10 s (`undo_token`) | S | US-6.5 | 4 |
| POST | `/applications/{application_id}/queue` | Queue for the selected lane | S | US-5.3 | 5 |
| POST | `/applications/{application_id}/dry-run` | Run a dry-run fill now | S | US-5.3 | 5 |
| GET | `/applications/{application_id}/attempts` | Attempts with proof file links | S | US-5.3, US-6.1 | 5 |
| GET | `/applications/{application_id}/one-tap-pack` | Prepared CV, cover note, answers, link | S | US-5.5 | 5 |
| POST | `/applications/{application_id}/confirm-applied` | "I applied" (one-tap/manual) | S, T:`actions:confirm_applied`, K | US-5.5 | 5 |
| GET | `/questions` | Open unknown questions | S, T:`actions:answer_question` | US-5.4 | 5 |
| POST | `/questions/{question_id}/answer` | Answer (optionally save to bank with scope) | S, T:`actions:answer_question`, K | US-5.4 | 5 |
| POST | `/documents/render` | Render/tailor a document (variant, job, toggles) | S | US-5.2 | 5 |
| GET | `/documents/{render_id}` | Render metadata, claim-check result, file links | S | US-5.2 | 5 |
| GET | `/files/{file_id}/download` | 302 to a short-lived signed URL | S | US-5.2 | 4 |

### 9.9 Inbox tracking, contacts, interviews, offers (`lifecycle`)
| Method | Path | Purpose | Auth | Story | Phase |
|---|---|---|---|---|---|
| POST | `/emails/{email_id}/link` | Confirm or change the application an email belongs to | S, T:`actions:confirm_link`, K | US-6.2 | 6 |
| GET | `/contacts` | Contacts (`?company_id`, `?relation`) | S | US-6.4 | 6 |
| POST | `/contacts` | Add contact | S | US-6.4 | 6 |
| PATCH | `/contacts/{contact_id}` | Edit contact | S | US-6.4 | 6 |
| GET | `/interviews` | Upcoming and past interviews | S | US-9.3 | 6 |
| POST | `/interviews` | Add interview round manually | S | US-9.3 | 6 |
| POST | `/interviews/{interview_id}/prep-pack` | Generate prep pack | S | US-9.3 | 9 |
| GET | `/offers` | Offers | S | US-9.4 | 6 |
| POST | `/offers` | Add offer figures | S | US-9.4 | 6 |
| PATCH | `/offers/{offer_id}` | Edit offer | S | US-9.4 | 6 |
| GET | `/offers/compare` | Cross-currency comparison with assumptions | S | US-9.4 | 9 |

### 9.10 Notifications and channels (`notify`)
| Method | Path | Purpose | Auth | Story | Phase |
|---|---|---|---|---|---|
| GET | `/digest/today` | Today's digest content | S, T:`read:summary` | US-4.4 | 4 |
| GET | `/notifications` | In-app notifications (cursor) | S | US-4.4 | 4 |
| POST | `/notifications/read` | Mark read (IDs or `all`) | S | US-4.4 | 4 |
| GET | `/notification-prefs` | Per-event channel preferences, quiet hours | S | US-4.4 | 4 |
| PUT | `/notification-prefs` | Replace preferences | S | US-4.4 | 4 |
| POST | `/push/subscriptions` | Register a web push subscription | S | US-4.4 | 4 |
| DELETE | `/push/subscriptions/{subscription_id}` | Remove a subscription | S | US-4.4 | 4 |
| POST | `/notify/telegram/link-code` | Create a one-time Telegram link code | S | US-4.4 | 4 |
| POST | `/notify/telegram/link` | Bot exchanges code + chat ID → per-user Telegram token | Bot service credential + code | US-4.4 | 4 |
| DELETE | `/notify/telegram/link` | Unlink Telegram (revokes token) | S | US-4.4 | 4 |
| POST | `/actions` | Execute a signed action (button in email/push/Telegram) | K | US-4.4 | 4 |

### 9.11 Strategy and insights (`strategy`, `insights`)
| Method | Path | Purpose | Auth | Story | Phase |
|---|---|---|---|---|---|
| GET | `/plan` | Active search plan (computed in memory before Phase 9) | S | US-9.2 | 4 |
| GET | `/plan/proposals` | Pending re-plan proposals with diff | S | US-9.2 | 9 |
| POST | `/plan/{version}/approve` | Approve proposal | S, K | US-9.2 | 9 |
| POST | `/plan/{version}/reject` | Reject proposal | S, K | US-9.2 | 9 |
| GET | `/insights/summary` | KPIs incl. interviews/week | S, T:`read:summary` | US-9.1 | 6 |
| GET | `/insights/funnel` | Funnel counts (`?from`, `?to`, `?dimension`) | S | US-9.5 | 6 |
| GET | `/insights/charts/{chart}` | Chart-ready series (`funnel`, `weekly_progress`, `callback_by_dimension`, `salary_comparison`, `offer_comparison`) | S | US-9.5 | 9 |
| GET | `/insights/weekly/{iso_week}` | Weekly report | S | US-9.1 | 9 |
| POST | `/events` | Product usage events (batch; no PII; respects opt-out) | S | — (PRODUCT_STANDARDS K) | 4 |

### 9.12 Privacy (`privacy`)
| Method | Path | Purpose | Auth | Story | Phase |
|---|---|---|---|---|---|
| POST | `/me/export` | Request full export (async) | S | US-10.7 | 10 |
| GET | `/me/export/{export_id}` | Export status | S | US-10.7 | 10 |
| GET | `/me/export/{export_id}/download` | 302 to signed URL (expires) | S | US-10.7 | 10 |
| POST | `/me/delete` | Request account deletion (grace period) | S (+ re-auth) | US-10.7 | 10 |
| POST | `/me/delete/cancel` | Cancel during grace period | S | US-10.7 | 10 |

### 9.13 Browser extension (`/ext`, `extension` → `apply`, `connectors`, `lifecycle`)
| Method | Path | Purpose | Auth | Story | Phase |
|---|---|---|---|---|---|
| GET | `/ext/status` | Pairing status, allowed hosts (from source policies), min version | E:`ext:read_profile_view` | US-8.3 | 8 |
| GET | `/ext/queue` | User's queued applications (one-tap and assisted) | E:`ext:read_profile_view` | US-8.3 | 8 |
| POST | `/ext/page-context` | Match an allowed-host page URL to a job (URL only) | E:`ext:assist` | US-8.3 | 8 |
| POST | `/ext/assist-plan` | Field mapping for an allowed ATS page (never a submit instruction) | E:`ext:assist` | US-8.3 | 8 |
| POST | `/ext/applications/{application_id}/proof` | Upload screenshot + payload after the user submits | E:`ext:record_proof` | US-8.3 | 8 |
| POST | `/ext/applications/{application_id}/confirm-applied` | Side panel "I applied" (one-tap hosts) | E:`ext:record_proof` | US-8.2 | 8 |
| GET | `/ext/applications/{application_id}/one-tap-pack` | Pack for the side panel copy buttons | E:`ext:read_profile_view` | US-8.2 | 8 |
| POST | `/ext/jobs/save` | Save current tab URL + title (explicit click) | E:`ext:save_job` | US-8.3 | 8 |

### 9.14 Home runner (`/runner`, optional)
| Method | Path | Purpose | Auth | Story | Phase |
|---|---|---|---|---|---|
| POST | `/runner/register` | Register runner (name, version) | R:`runner:pull` | US-8.1 | 8 |
| POST | `/runner/heartbeat` | Heartbeat (+ `submitting` signal) | R:`runner:pull` | US-8.1 | 8 |
| POST | `/runner/tasks/lease` | Lease next task (long-poll ≤ 25 s) | R:`runner:pull` | US-8.1 | 8 |
| POST | `/runner/tasks/{task_id}/result` | Report result | R:`runner:report` | US-8.1 | 8 |
| POST | `/runner/uploads` | Upload screenshot / payload snapshot | R:`runner:report` | US-8.1 | 8 |

### 9.15 Admin (`/admin`, operational data only)
| Method | Path | Purpose | Auth | Story | Phase |
|---|---|---|---|---|---|
| GET | `/admin/connectors` | Source health, last runs, degraded flags | S+MFA, A:`admin:read` | US-2.6, US-10.8 | 4 |
| POST | `/admin/companies/verify` | Run catalogue verification | S+MFA | US-2.7 | 4 |
| GET | `/admin/queues` | Queue depth and latency | S+MFA, A:`admin:read` | US-10.8 | 4 |
| GET | `/admin/dead-letters` | Dead letters | S+MFA, A:`admin:dead_letters` | US-10.8 | 4 |
| POST | `/admin/dead-letters/{dead_letter_id}/replay` | Replay | S+MFA, A:`admin:dead_letters` | US-10.8 | 4 |
| POST | `/admin/dead-letters/{dead_letter_id}/discard` | Discard | S+MFA, A:`admin:dead_letters` | US-10.8 | 4 |
| GET | `/admin/flags` | Global flags | S+MFA, A:`admin:read` | US-4.6 | 4 |
| PUT | `/admin/flags/{key}` | Set global flag (market/role flags refuse unless conformance green) | S+MFA, A:`admin:flags` | US-4.6, US-10.10 | 4 |
| GET | `/admin/rollout` | Market/role rollout checklist status | S+MFA, A:`admin:read` | US-10.10 | 4 |
| GET | `/admin/llm-usage` | LLM usage, cost per MAU, Tier 2 coverage | S+MFA, A:`admin:read` | US-3.6, US-3.7 | 4 |
| GET | `/admin/audit` | Audit log search | S+MFA | US-10.8 | 4 |
| GET | `/admin/users` | User directory (no content) | S+MFA | US-10.8 | 10 |
| PUT | `/admin/users/{user_id}/role` | Change role (owner only) | S+MFA (owner) | US-10.8 | 10 |
| PUT | `/admin/users/{user_id}/plan` | Change plan / overrides | S+MFA | US-10.5 | 10 |
| GET | `/admin/users/{user_id}/content` | Read user content under an active support grant | S+MFA + grant | US-10.8 | 10 |
| GET | `/admin/abuse` | Abuse signals queue | S+MFA | US-10.6 | 10 |
| POST | `/admin/abuse/{signal_id}/review` | Review: dismiss, cooldown, suspend | S+MFA | US-10.6 | 10 |
| POST | `/admin/invites` | Create invite | S+MFA | US-10.1 | 10 |

### 9.16 Totals
147 operations: 2 health, 20 auth/account, 7 controls, 4 packs/legal, 12 profile,
11 inboxes/companies/consents (incl. the logo proxy), 9 matches/jobs, 15 applications/documents, 11 lifecycle extras,
11 notifications, 9 strategy/insights, 5 privacy, 8 extension, 5 runner, 18 admin.
(`DELETE /push/subscriptions/{id}` and `DELETE /notify/telegram/link` were added here to make
revocation complete.)

## 10. Contract testing

- `docs/openapi.yaml` is the contract. CI checks:
  1. The spec is valid OpenAPI 3.1 (lint).
  2. **Drift check:** the FastAPI app's generated schema is compared with `docs/openapi.yaml`
     (paths, methods, parameters, request/response schemas, status codes). Any difference fails CI
     until one of them is updated in the same PR.
  3. **Contract tests** (Schemathesis-style property tests against the spec, run on a test database)
     for every implemented operation: status codes, problem bodies and response shapes. The tool
     choice needs dependency approval when Phase 4 starts.
  4. The generated TypeScript client (`frontend/packages/api-client`) is regenerated from the spec;
     CI fails if the committed client is stale.
  5. **Isolation suite:** for every operation that takes a resource ID, user B's credentials against
     user A's resource must return 404 (ADR-0017).
- Operations that are not implemented yet are tagged `x-phase: <n>` in the spec; the drift check
  only enforces operations whose phase is ≤ the current phase in `docs/progress.md`.
