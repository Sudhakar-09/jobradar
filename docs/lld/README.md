# Low-Level Design (LLD)

One file per module. Each file is the contract for implementing that module: code that disagrees
with its LLD is a bug in one of them, fixed in the same PR.

| File | Module | Main PRD stories | Phase |
|---|---|---|---|
| [database.md](database.md) | All tables, indexes, constraints, RLS, migration rules | — | all |
| [state-machine.md](state-machine.md) | Application states, transitions, triggers, guards | US-5.x, US-6.x | 5–6 |
| [profile.md](profile.md) | Profile, resume parsing, variants, answer bank, embeddings | US-1.x | 1, 3, 5 |
| [connectors.md](connectors.md) | Sources, ATS/aggregator connectors, alert inbox + parsers, company catalogue, source policies | US-2.x | 2 |
| [normalizer.md](normalizer.md) | Ingest, dedupe, normalization, job embeddings, compensation models | US-2.3, US-3.1, US-3.5 | 2–3 |
| [matching.md](matching.md) | Tiered matching, eligibility rules, fit scoring, ranking | US-3.2 … US-3.8 | 3 |
| [documents.md](documents.md) | Variant selection, tailoring, claim check, rendering (DOCX/PDF, RTL) | US-5.1, US-5.2 | 5 |
| [apply.md](apply.md) | Apply adapters, guards, dry-run, proof, unknown questions, one-tap packs, assist plans | US-5.3 … US-5.5, US-6.1 | 5–6 |
| [lifecycle.md](lifecycle.md) | State transitions, inbox tracking, follow-ups, ghosting, interviews, offers, contacts | US-6.x, US-9.3, US-9.4 | 6, 9 |
| [notify.md](notify.md) | Outbox, channels (in-app, email, push, Telegram), digest, preferences | US-4.4, US-4.5 | 4 |
| [strategy.md](strategy.md) | SearchPlan from profile + packs, weekly re-plan | US-9.2 | 9 |
| [insights.md](insights.md) | Funnel, metrics, weekly report, product events | US-9.1, US-9.5 | 9 |
| [runner.md](runner.md) | Optional home runner protocol and client | US-8.1 | 8 |
| [extension.md](extension.md) | Browser extension (assist, side panel, pairing) | US-8.2, US-8.3 | 8 |
| [accounts.md](accounts.md) | Auth, sessions, tokens, roles, invites, support grants | US-4.2, US-10.1 | 4, 10 |
| [privacy.md](privacy.md) | Consent, export, deletion | US-10.3, US-10.7 | 2 (minimal), 10 |
| [quotas.md](quotas.md) | Plans, usage counters, LLM budgets, anti-abuse, restrictions | US-3.6, US-10.5, US-10.6 | 3, 10 |
| [admin.md](admin.md) | Admin console services (operational data only) | US-4.6, US-10.8 | 4, 10 |

## Required sections in every module LLD

1. **Header:** status, version, owner module, PRD stories, ADRs, phase.
2. **Responsibilities** and **must NOT do** (explicit non-responsibilities and forbidden actions).
3. **Public interface (typed):** service functions with Python signatures, Pydantic input/output
   models and documented exceptions. This is everything other modules may import.
4. **Internal design:** class diagram (Mermaid `classDiagram`) and at least one sequence diagram
   (Mermaid `sequenceDiagram`) for the main flow.
5. **Data owned:** tables (linking to `database.md` sections), columns this module writes, indexes
   it relies on, jsonb models it defines.
6. **Error handling, retries, idempotency:** exception mapping, retry policy, idempotency keys,
   what happens on partial failure.
7. **Config and feature flags:** settings (pydantic-settings), pack fields used, flags read.
8. **Metrics and log events:** Prometheus metric names and labels; structlog event names and
   fields (no PII).
9. **Security and privacy notes:** untrusted inputs, PII handled, tenancy.
10. **Test plan:** unit, integration, fixture/golden, conformance, synthetic, and isolation tests
    with the concrete cases that must exist.
11. **Open questions.**

## Shared types (defined in `core`, used by every module)

```python
# core/scope.py
@dataclass(frozen=True, slots=True)
class UserScope:
    user_id: UUID
    roles: frozenset[Role]                 # Role(StrEnum): USER, ADMIN, OWNER
    via: ClientKind                        # WEB, EXTENSION, TELEGRAM, RUNNER, SYSTEM, ADMIN_API
    token_scopes: frozenset[str] = frozenset()   # empty for web sessions (full user rights)
    correlation_id: UUID

SYSTEM_SCOPE: Final = ...                  # for shared-corpus work only; cannot touch user tables

# core/clock.py
class Clock(Protocol):
    def now(self) -> datetime: ...         # tz-aware UTC; injected for tests

# core/ids.py
def new_id() -> UUID: ...                  # UUIDv7

# core/errors.py — full hierarchy in docs/coding-standards.md (Step 5)
class JobRadarError(Exception): code: ClassVar[str]
class NotFoundError(JobRadarError)          # also used for cross-tenant access (never 403-leak existence)
class ValidationFailedError(JobRadarError)
class PermissionDeniedError(JobRadarError)
class ConflictError(JobRadarError)
class ConcurrencyConflictError(ConflictError)
class InvalidTransitionError(ConflictError)
class GuardFailedError(JobRadarError): guard: GuardCode
class QuotaExceededError(JobRadarError): metric: str; resets_at: datetime
class ConsentRequiredError(JobRadarError): source: str
class ExternalServiceError(JobRadarError): service: str; retryable: bool
class RateLimitedError(ExternalServiceError): retry_after: float | None
class SchemaDriftError(ExternalServiceError)
class LlmOutputInvalidError(JobRadarError)
class BudgetExceededError(QuotaExceededError)

# core/llm.py (gateway used by every LLM-using module)
class LlmGateway(Protocol):
    async def complete_json[T: BaseModel](
        self, scope: UserScope | SystemScope, *, task: str, prompt: PromptRef,
        variables: Mapping[str, object], schema: type[T], tier: ModelTier,
        cache_key: bytes | None = None, timeout_s: float = ...,
    ) -> LlmResult[T]: ...                 # budget pre-check, cache, metering, one repair retry
    async def complete_json_batch[T: BaseModel](...) -> list[LlmResult[T]]: ...
    async def embed(self, scope, *, texts: Sequence[str], model: str) -> list[Vector]: ...

# core/plugins.py — registries loaded from entry points; read-only after startup
class Registry[P](Protocol):
    def get(self, code: str) -> P: ...     # raises NotFoundError
    def all(self) -> Mapping[str, P]: ...
```

Untrusted text (job descriptions, emails, page content, form labels) is always wrapped in an
`Untrusted[str]` marker type. It can be passed to the LLM gateway only as a data variable,
never interpolated into prompt instructions, and is never logged.

More shared types (`core`):

```python
class Page[T](BaseModel):  # cursor pagination for every list endpoint (spec: `Page` + `<Model>Page`)
    items: list[T]
    next_cursor: str | None
    has_more: bool


class SignedFileRef(BaseModel):  # short-lived download URL for a `files` row
    file_id: UUID
    url: HttpUrl
    expires_at: datetime
    content_type: str
    name: str | None = None  # suggested download file name


class UploadRef(BaseModel):  # result of a size-limited upload endpoint (runner, extension)
    upload_id: UUID
    sha256: str
    size_bytes: int
    content_type: str


class MoneyAmount(BaseModel):  # JSON: amount is a decimal string (api.md §3)
    amount: Decimal
    currency: CurrencyCode
    period: SalaryPeriod | None = None  # normalizer.SalaryPeriod; None for one-off amounts
```

### API transport and core types

Mirrors `docs/openapi.yaml` `components/schemas`: same names, fields, enums and optionality (Step 4 review: the LLD is the single source of truth, the spec must match it). Optional fields are `T | None = None` and serialized with `exclude_none`; `XPage = Page[X]` is the cursor envelope from `docs/lld/README.md`; `# read-only` fields are ignored on input. Types not defined here come from their owning module (see the shared-model ownership table in `docs/lld/README.md`). These are owned by `core` (transport, health, files, packs loader).

```python
class Accepted(BaseModel):
    """Asynchronous work accepted."""
    id: UUID | None = None  # read-only
    status: str


class FileKind(StrEnum):
    RESUME_UPLOAD = "resume_upload"
    RENDERED_DOCUMENT = "rendered_document"
    SCREENSHOT = "screenshot"
    PAYLOAD_SNAPSHOT = "payload_snapshot"
    EXPORT = "export"
    PHOTO = "photo"


class HealthStatus(BaseModel):
    status: Literal["ok"]


class MarketPackSummary(BaseModel):
    code: str
    name: str
    currency: CurrencyCode  # ISO 4217 currency
    locales: list[str]
    rtl: bool
    cv_format: str
    last_verified: date | None = None


MarketPackSummaryPage = Page[MarketPackSummary]


class MessageRef(BaseModel):
    """Message key + ICU params; the client renders it in the user's locale."""
    key: str
    params: dict[str, JsonValue] | None = None


class PersonaPackSummary(BaseModel):
    code: str
    description: str
    daily_volume_range: list[int]


PersonaPackSummaryPage = Page[PersonaPackSummary]


class Problem(BaseModel):
    """RFC 9457 problem details, extended with code, detail_key, params and correlation_id."""
    type: HttpUrl
    title: str
    status: int
    code: Literal["bad_request", "unauthenticated", "forbidden", "csrf_failed", "mfa_required", "not_found", "conflict", "invalid_transition", "concurrency_conflict", "guard_failed", "precondition_failed", "validation_failed", "client_outdated", "consent_required", "rate_limited", "quota_exceeded", "budget_exceeded", "upstream_error", "upstream_unavailable", "paused", "internal_error"]
    detail_key: str | None = None
    params: dict[str, JsonValue] | None = None
    correlation_id: UUID
    errors: list[ValidationErrorItem] | None = None


class ReadinessStatus(BaseModel):
    status: Literal["ok", "degraded"]
    checks: dict[str, str]


class RolePackSummary(BaseModel):
    code: str
    field: str | None = None
    family: str | None = None
    title_aliases: list[str]
    signal_documents: list[str]


RolePackSummaryPage = Page[RolePackSummary]


UntrustedText = str  # Third-party or LLM-derived text. Render as plain text only, never as HTML.


class ValidationErrorItem(BaseModel):
    field: str
    key: str
    params: dict[str, JsonValue] | None = None
```

## Conventions used in every LLD

- **Async:** service functions that do I/O are `async def`; pure functions (rules, ranking,
  composition, formatting) are plain `def`. Signatures in LLDs follow this rule.
- **Ownership of DTOs:** each shared model is defined once, in the module listed below, and imported
  by others under the same name.

  | Model | Owner | Used by |
  |---|---|---|
  | `ProfileView`, `CvContent`, `AnswerMatch`, `AnswerView`, `ResumeVariant` | profile | matching, strategy, documents, apply |
  | API: `SeniorityLevel`, `LocationPref`, `LanguageSkill`, `CredentialView`, `SalaryExpectation`, `AnswerScope` | profile | matching, apply, admin |
  | `RawJob`, `SourcePolicy`, `InboundMessage`, API `AccessMode` | connectors | normalizer, apply, matching, extension, runner |
  | `NormalizedJob`, `CompInput`, `CompProfile`, `CompBreakdown`, `JobDimensions`; API `Assumption`, `Deduction`, `SalaryPeriod`, `SalaryBasis`, `RemoteType`, `EmploymentType`, `VisaSponsorship` | normalizer | matching, profile, lifecycle, notify, extension, admin |
  | `RankedJob`, `JobSummary`, `EligibilityReason`, `Explanation`; API `JobCard`, `MatchItem`, `ScoreBreakdown` | matching | notify, documents, lifecycle, apply, extension, admin |
  | `RenderedDocument`, `OneTapPack`, `FieldToggles`, API `RenderedDocumentLinks`, `PreparedAnswer` | documents | apply, extension, lifecycle, profile |
  | `FormPlan`, `AssistPlan`, `AssistField`, `ExtensionProof`, `ExternalAttemptResult`, `SubmittedPayload`, `Lane`; API `FieldType`, `ConfirmAppliedRequest` | apply | runner, extension, lifecycle, matching, strategy, admin |
  | `TransitionRequest`, `EventDetail`, `GuardSnapshot`, `ApplicationView`, `CreateApplication`, `DigestCounts`; API `ApplicationState`, `StateReason`, `AppliedVia`, `TransitionTrigger`, `GuardCode`, `EventView` | lifecycle (state-machine.md §6) | apply, matching, runner, extension, notify, admin |
  | `NotificationEvent`, `Message`, `ActionSpec`, `PublishRequest` | notify | every publisher |
  | `SearchPlan`, `PlanDiff` | strategy | matching, notify, insights |
  | `PerformanceSnapshot`, `RateStat`, `ChartData`, API `DateRange` | insights | strategy, admin, web app |
  | `Metric`, `LimitKey`, `PlanLimits`, `QuotaDecision` | quotas | every metered module, strategy, admin |
  | `UserPreferences` (`users.preferences`), API `Role`, `UserStatus` | accounts | lifecycle, notify, insights, admin |
  | API `Flag`, `FlagUpdate`, `StatusSummary`, `LaneStatus`, `PauseRequest` (control endpoints over `core.flags`) | admin | web app, Telegram bot |
  | API transport: `Page`, `MessageRef`, `MoneyAmount`, `Problem`, `ValidationErrorItem`, `UntrustedText`, `SignedFileRef`, `UploadRef`, `Accepted`, `FileKind`; pack summaries | core (README) | every module |
  | `ConsentSource`, `ConsentGrant` | privacy | connectors, lifecycle, notify, extension, runner |

- **Metric names** are written in LLDs without a namespace; the Prometheus registry is created with
  namespace `jobradar`, so the exported name is `jobradar_<name>`. Counters end in `_total`,
  durations in `_seconds`, ratios in `_ratio`; base units only.
- **Log event names** are `<module>.<event>` in snake_case (for example
  `lifecycle.transitioned`). **Audit actions** are `<object>.<verb_past>` (for example
  `application.submitted`).

## Core components (no separate LLD)

| Component | Responsibility | Stories |
|---|---|---|
| `core.settings`, `core.health`, `core.logging` | Typed settings, `/health` and `/ready`, structlog with correlation IDs | US-0.1 |
| `core.packs` | Load and validate market, role and persona packs (schemas extended at Phase 2 start: currency conventions, locale/RTL, CV field defaults, sources with access modes, `compensation_model`; role credentials per market and hiring patterns; persona `followup_days`, `default_llm_top_n`, `default_min_fit_score`, `onboarding_steps`) | US-1.2, US-10.9 |
| `tests/conformance/` | Pack conformance suite parametrized over every pack (PRD §8a.1); results published for the rollout gate (admin.md) | US-2.9, US-10.9, US-10.10 |
| `core.flags` (`FlagService`) | Read flags (global + per user, cached ≤ 5 s); the only writer is the admin path; emits `flags.changed` | US-4.5, US-4.6 |
| `core.llm` (`LlmGateway`) | Provider abstraction, prompts, schemas, cache, metering into `llm_calls`, budget pre-check via quotas | US-3.6, US-3.7 |
| `core.files` (`FileStore`) | Encrypted object storage and the `files` index; signed URLs | US-1.4, US-5.2, US-6.1 |
| `frontend/` | Design system, web app, extension UI — specified in `docs/design-system.md` and `docs/ux.md` (Step 6) and tested by the UI matrix | US-4.1, US-4.3, US-4.7, US-6.5, US-9.5, US-10.2, US-11.1, US-11.3 |

## Canonical identifiers

This is the single reference list. LLDs, code and tests use these exact strings.

### Flags (`settings_flags.key`; scope global, user or both)

| Key | Scope | Default | Read by |
|---|---|---|---|
| `PAUSE_ALL` | global + user | off | apply, runner, extension, lifecycle guards, notify (banner) |
| `lane.<auto\|careful\|assisted\|one_tap>.enabled` | global + user | auto off, careful off, assisted on, one_tap on | apply, strategy, guards |
| `apply.live_submit.enabled` | global + user (per lane value) | off | apply, strategy, guards |
| `apply.dry_run_reviewed_at` | user | unset | apply (gate for live submit) |
| `apply.adapter.<code>.enabled` | global | on once fixtures pass | apply |
| `connector.<code>.enabled` | global | on for Phase 2 sources | connectors |
| `alerts.inbox.gmail.enabled`, `alerts.inbox.forwarding.enabled` | global | on / off | connectors |
| `market.<code>.enabled`, `role.<code>.enabled` | global + user | india, uae, java_backend on | connectors, matching, strategy (gate in admin) |
| `normalizer.llm.enabled` | global | on | normalizer |
| `profile.llm_resume_parser.enabled` | global | off until the LLM gateway exists | profile |
| `matching.tier1.enabled` | global | off until embeddings exist | matching |
| `documents.tailoring.enabled` | global + user | on | documents |
| `inbox_tracking.enabled` | global + user | off (Phase 6, consent-gated) | lifecycle |
| `channel.<email\|web_push\|telegram>.enabled` | global | on | notify |
| `strategy.replan.enabled` | global + user | on (Phase 9) | strategy |
| `insights.weekly_report.enabled` | user | on (Phase 9) | insights |
| `product_events.enabled` | global | on (respects `users.preferences.analytics_opt_out`) | insights |
| `extension.enabled`, `extension.assist.enabled` | global + user | off until Phase 8 / on after pairing | extension |
| `runner.enabled` | user | off | runner |
| `signup.mode` | global | `closed` | accounts |
| `quotas.enforce` | global | `soft` (Stage 1) | quotas |
| `abuse.auto_cooldown.enabled` | global | on (Phase 10) | quotas |
| `prompt.<name>.version` | global | from settings `prompts.<name>.version` | LLM gateway |

Global settings (not flags) referenced across modules: `matching.global_min_fit_floor` (60),
`matching.llm_top_n` (10), `matching.top_k` (50), `fx.rates`, `fx.pegs`, `fx.max_age_days`,
`llm.models.{small,standard,premium,embedding}`.

### Quota metrics and plan-limit keys (quotas.md)

Metered: `applications.auto`, `applications.assisted`, `applications.total`,
`applications.per_employer` (rolling 30 days, keyed by company), `documents.tailored`,
`llm.tokens`, `llm.cost_usd_micros` (monthly), `llm.score_on_demand`, `alerts.ingested`,
`storage.bytes`. Non-metered limits: `matching.llm_top_n`, `documents.premium_model_allowed`.

### Consent sources (privacy.md)

`terms`, `privacy_policy`, `gmail_alerts`, `gmail_inbox`, `forwarding_inbox`, `extension`,
`telegram`, `web_push`, `runner`, `portal:<host>`.

### Notification events (notify.md; `notifications.event` CHECK)

`digest`, `question`, `interview_invite`, `offer`, `followup_due`, `weekly_report`, `security`,
`status_change`, `reminder`, `needs_review`, `apply_failed`.

### Domain events (in-process / Celery chaining; payloads are IDs only)

| Event | Emitted by | Consumed by |
|---|---|---|
| `jobs.normalized` | normalizer | matching (`match_user` fan-out) |
| `applications.transitioned` | lifecycle (after commit) | insights (late-event rollup), notify (via outbox rows written in the same transaction) |
| `flags.changed` | core flag service | strategy (safety narrowing), caches, extension status |

### Guard codes (state-machine.md §7) and gate codes

Guards: `paused`, `lane_disabled`, `restricted`, `below_quality`, `cap_reached`, `duplicate`,
`source_policy`, `consent_missing`, `deleting`. Flag gate (admin): `rollout_incomplete`,
`conformance_failing`.

### Other enumerations

- Triggers: `system`, `email`, `user`, `extension`, `runner`, `admin`.
- Lanes: `auto`, `careful`, `assisted`, `one_tap`. `applied_via`: `server`, `extension`, `runner`,
  `manual`.
- Application states and `state_reason` values: database.md §3.8 / state-machine.md §2, §5.
- Access modes (source policies): `api`, `ats_feed`, `alert_email`, `extension_assist`,
  `server_apply`, `one_tap`, `none`.
- Config files: `config/source_policies.yaml`, `config/connectors.yaml`,
  `config/alert_senders.yaml`, `config/companies.yaml`, `config/plans.yaml`,
  `config/compensation/<market>/<date>.yaml`, `config/consents/`.

## Traceability

Endpoints: **see `docs/api.md` / `docs/openapi.yaml`**. All paths are under `/api/v1`.

| Story | Modules | Tables | Endpoints |
|---|---|---|---|
| US-0.1 | core | — | `GET /health`, `GET /ready` |
| US-1.1 | profile | profiles (YAML until Phase 3) | `GET /profile`, `PATCH /profile` |
| US-1.2 | core.packs, conformance | — | `GET /packs/markets`, `GET /packs/roles`, `GET /packs/personas` |
| US-1.3 | profile | answer_bank | `GET /answers`, `POST /answers`, `PATCH /answers/{answer_id}`, `DELETE /answers/{answer_id}` |
| US-1.4 | profile, core.files | files, profiles | `POST /profile/resume`, `POST /profile/resume/apply` |
| US-2.1 | connectors, normalizer | companies, source_runs, jobs, job_sources | admin `GET /admin/connectors` |
| US-2.2 | connectors | source_runs | admin `GET /admin/connectors` |
| US-2.3 | normalizer | jobs, job_sources | — (internal) |
| US-2.4 | connectors (CLI) | source_runs | — (CLI `jobradar discover`) |
| US-2.5 | connectors, privacy | alert_inboxes, alert_messages, consents, job_sources | `POST /inboxes/gmail/connect`, `GET /inboxes`, `DELETE /inboxes/{inbox_id}`, `POST /consents`, `DELETE /consents/{source}` |
| US-2.6 | connectors, admin | source_runs | `GET /admin/connectors` |
| US-2.7 | connectors | companies, company_suggestions | `GET /companies/suggestions`, `POST /companies/suggestions/{suggestion_id}/decision`; admin `POST /admin/companies/verify` |
| US-2.8 | connectors (policies), apply, extension | — | `GET /ext/status` (policy snapshot) |
| US-2.9 | conformance, normalizer, connectors, admin | settings_flags | `PUT /admin/flags/{key}` (gate) |
| US-3.1 | normalizer | jobs, job_embeddings | — (internal) |
| US-3.2 | matching | job_scores | `GET /jobs/{job_id}/explain` |
| US-3.3 | matching | job_scores, llm_calls | `POST /jobs/{job_id}/score` |
| US-3.4 | matching | job_scores | `GET /matches` (CLI `jobradar matches --top 20` in Phase 3) |
| US-3.5 | normalizer, matching | jobs | `GET /jobs/{job_id}` (pay comparison block) |
| US-3.6 | core.llm, quotas | llm_calls, usage_counters, plans, user_plans | `GET /me/usage` |
| US-3.7 | matching, normalizer, profile | job_embeddings, profile_embeddings, job_scores | `GET /matches/possible`, `POST /jobs/{job_id}/score` |
| US-3.8 | all pipeline modules (tests) | — | — |
| US-4.1 | frontend (Step 6) | — | — |
| US-4.2 | accounts | users, credentials, oauth_identities, sessions | `POST /auth/login`, `POST /auth/google`, `POST /auth/logout`, `POST /auth/logout-everywhere`, `GET /me`, `PATCH /me` |
| US-4.3 | matching, normalizer, lifecycle | job_scores, applications, job_feedback | `GET /matches`, `GET /jobs/{job_id}`, `POST /jobs/{job_id}/apply`, `POST /jobs/{job_id}/skip`, `POST /jobs/{job_id}/save`, `PUT /jobs/{job_id}/feedback` |
| US-4.4 | notify, matching | notifications, notification_prefs, channel_links, push_subscriptions | `GET /digest/today`, `GET /notifications`, `POST /notifications/read`, `GET /notification-prefs`, `PUT /notification-prefs`, `POST /push/subscriptions`, `POST /notify/telegram/link-code`, `POST /notify/telegram/link`, `POST /actions`, `DELETE /push/subscriptions/{subscription_id}`, `DELETE /notify/telegram/link` |
| US-4.5 | core.flags, apply, notify | settings_flags | `POST /control/pause`, `POST /control/resume`, `GET /me/status` |
| US-4.6 | admin, core.flags | settings_flags, audit_log | `GET /admin/flags`, `PUT /admin/flags/{key}`, `PATCH /flags/{key}` (bot) |
| US-4.7 | frontend (Step 5/6) | — | — |
| US-5.1 | documents, profile | resume_variants, document_renders | `GET /resume-variants`, `POST /resume-variants`, `PATCH /resume-variants/{variant_id}` |
| US-5.2 | documents | document_renders, files | `POST /documents/render`, `GET /documents/{render_id}`, `GET /files/{file_id}/download` |
| US-5.3 | apply | apply_attempts, files | `POST /applications/{application_id}/dry-run`, `GET /applications/{application_id}/attempts` |
| US-5.4 | apply, profile, notify | pending_questions, answer_bank | `GET /questions`, `POST /questions/{question_id}/answer` |
| US-5.5 | apply, documents, lifecycle | applications, document_renders | `GET /applications/{application_id}/one-tap-pack`, `POST /applications/{application_id}/confirm-applied` |
| US-6.1 | apply, quotas, lifecycle | apply_attempts, applications, usage_counters | `POST /applications/{application_id}/queue`, `POST /me/dry-run-review` |
| US-6.2 | lifecycle, connectors, privacy | emails, consents | `POST /consents` (`gmail_inbox`), `POST /emails/{email_id}/link` |
| US-6.3 | lifecycle, notify | applications, application_events, notifications | — (scheduled) |
| US-6.4 | lifecycle | contacts | `GET /contacts`, `POST /contacts`, `PATCH /contacts/{contact_id}` |
| US-6.5 | lifecycle | applications, application_events | `GET /applications`, `GET /applications/{application_id}`, `POST /applications/{application_id}/transition`, `POST /events/{event_id}/undo`, `GET /applications/{application_id}/history` |
| US-7.1 | admin, core | dead_letters, source_runs | `GET /admin/queues`, `GET /admin/dead-letters`, `POST /admin/dead-letters/{dead_letter_id}/replay` |
| US-8.1 | runner, apply, accounts | runners, runner_tasks, client_tokens | `POST /runner/register`, `POST /runner/heartbeat`, `POST /runner/tasks/lease`, `POST /runner/tasks/{task_id}/result`, `POST /runner/uploads`, `POST /tokens` (runner) |
| US-8.2 | extension, apply, documents | applications, document_renders | `GET /ext/queue`, `GET /ext/applications/{application_id}/one-tap-pack`, `POST /ext/applications/{application_id}/confirm-applied` |
| US-8.3 | extension, apply, accounts, connectors | extension_installs, client_tokens, auth_challenges, apply_attempts | `POST /auth/pair/start`, `POST /auth/pair/exchange`, `GET /ext/status`, `POST /ext/page-context`, `POST /ext/assist-plan`, `POST /ext/applications/{application_id}/proof`, `POST /ext/jobs/save` |
| US-9.1 | insights, notify | metrics_daily, notifications | `GET /insights/weekly/{iso_week}` |
| US-9.2 | strategy, insights | search_plans | `GET /plan`, `GET /plan/proposals`, `POST /plan/{version}/approve`, `POST /plan/{version}/reject` |
| US-9.3 | lifecycle | interviews | `GET /interviews`, `POST /interviews`, `POST /interviews/{interview_id}/prep-pack` |
| US-9.4 | lifecycle, normalizer | offers | `GET /offers`, `POST /offers`, `PATCH /offers/{offer_id}`, `GET /offers/compare` |
| US-9.5 | insights | metrics_daily, product_events | `GET /insights/summary`, `GET /insights/funnel`, `GET /insights/charts/{chart}`, `POST /events` |
| US-10.1 | accounts | users, credentials, invites, auth_challenges, sessions | `POST /auth/signup`, `POST /auth/verify-email`, `POST /auth/password-reset/request`, `POST /auth/password-reset/complete`, `POST /auth/totp/enroll`, `POST /auth/totp/confirm`, `POST /auth/totp`, `POST /admin/invites` |
| US-10.2 | profile, strategy, privacy, notify, frontend | profiles, consents, notification_prefs | (composes US-1.4, US-2.5, US-4.4, US-3.4 endpoints) `GET /onboarding/status` |
| US-10.3 | privacy | consents | `GET /consents`, `POST /consents`, `DELETE /consents/{source}` |
| US-10.4 | accounts, all repositories | all user-owned tables (RLS) | `GET /tokens`, `DELETE /tokens/{token_id}` (+ isolation suite over every endpoint) |
| US-10.5 | quotas | plans, user_plans, usage_counters | `GET /me/usage`; admin `PUT /admin/users/{user_id}/plan` |
| US-10.6 | quotas, apply, admin | abuse_signals, user_restrictions | admin `GET /admin/abuse`, `POST /admin/abuse/{signal_id}/review` |
| US-10.7 | privacy | export_jobs, deletion_jobs, files | `POST /me/export`, `GET /me/export/{export_id}`, `GET /me/export/{export_id}/download`, `POST /me/delete`, `POST /me/delete/cancel` |
| US-10.8 | admin, accounts | support_grants, audit_log, settings_flags | `GET /admin/users`, `PUT /admin/users/{user_id}/role`, `GET /admin/llm-usage`, `GET /admin/audit`, `POST /support-grants`, `DELETE /support-grants/{grant_id}`, `GET /admin/users/{user_id}/content`, `POST /admin/dead-letters/{dead_letter_id}/discard` |
| US-10.9 | core.packs, conformance | — | — |
| US-10.10 | admin | settings_flags | `GET /admin/rollout`, `PUT /admin/flags/{key}` |
| US-11.1 | accounts, privacy, frontend | users, consents | `POST /auth/signup` (open mode), `GET /legal/{doc}` |
| US-11.2 | connectors | alert_inboxes, alert_messages | `POST /inboxes/forwarding`, inbound webhook `POST /inbound/mail` (provider-signed) |
| US-11.3 | notify, documents, frontend | — | — |
| US-11.4 | connectors, matching (load tests) | — | — |
| US-11.5 | quotas | plans | `GET /plans` |
