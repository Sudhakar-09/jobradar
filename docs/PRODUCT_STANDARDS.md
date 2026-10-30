# JobRadar — Product Standards A to Z

> Place this file at `docs/PRODUCT_STANDARDS.md`. It extends CLAUDE.md.
> Principle: **design for scale, build for one.** Every item below is designed in from day one,
> but implemented at the size the product needs now. Prefer open-source, self-hostable tools.

---

## A — Auth & accounts
- Users, sessions, roles (`owner`, `admin`, `user`) from day one, even with one user.
- Password hashing with argon2; optional login with Google OAuth.
- Scoped API tokens: dashboard, Telegram bot and home runner each get their own token with least privilege; tokens revocable.
- Per-user data isolation enforced in the service layer (every query filtered by `user_id`) and covered by tests.
- ✅ Done when: a second test user cannot read or change the first user's data through any endpoint.

## B — Backups & disaster recovery
- Nightly `pg_dump` (compressed, encrypted) to off-server storage; keep 7 daily + 4 weekly.
- Documented, scripted restore; a monthly restore test task that restores into a scratch DB and checks row counts.
- Targets: RPO ≤ 24h, RTO ≤ 2h.
- ✅ Done when: `make restore-test` passes.

## C — CI/CD
- GitHub Actions: lint (ruff), type check (mypy), unit + integration tests, coverage gate, Docker build, dependency + container vulnerability scan (pip-audit, Trivy), secret scan (gitleaks).
- Images tagged with git SHA and semver; pushed to GitHub Container Registry.
- Deploy job (manual approval) to production via SSH + `docker compose pull && up -d`, followed by smoke test; automatic rollback to previous tag if smoke test fails.

## D — Data quality & connector health
- Every connector run records: duration, jobs found, new, updated, errors, HTTP status breakdown.
- Schema-drift detection: if a source response no longer matches its Pydantic model, mark connector `degraded` and alert.
- Anomaly checks: alert if a source returns 0 jobs or a >70% drop versus its 7-day average.
- Data freshness metric per source (time since last successful run).
- Dedupe quality: daily report of suspected duplicates that slipped through.

## E — Environments & configuration
- `dev` (local), `staging` (optional, same compose), `prod`. Identical images, config only via environment.
- Typed settings (pydantic-settings) validated at startup; app refuses to start with missing/invalid config.
- `.env.example` documents every variable.

## F — Feature flags
- Simple DB-backed flags (or Unleash later): per-lane enable, per-connector enable, live-submit enable, new prompt versions.
- Togglable from admin console and Telegram (`/flag lane_naukri off`).

## G — Guardrails for automation
- Global kill switch, per-lane daily caps, per-source rate limits, random human-like delays.
- Idempotency key per (user, job) — an application can never be submitted twice.
- Respect each source's terms: official/public APIs first; prohibited platforms stay one-tap only.
- Every submission stores screenshot + submitted payload + prompt/model versions used.

## H — Health checks & self-healing
- `/health` (process alive) and `/ready` (DB, Redis, queue reachable) on every service.
- Docker restart policies + healthchecks; Celery worker auto-restart after N tasks (memory leaks).
- Stuck-task watchdog: tasks running beyond their timeout are killed and retried or dead-lettered.

## I — Incident management
- Severity levels (SEV1 user-facing apply errors, SEV2 source down, SEV3 degraded).
- Runbooks in `docs/runbooks/` for: source down, LLM provider down, DB full, queue backlog, duplicate-application suspicion, Gmail token expired, home runner offline.
- Lightweight postmortem template in `docs/postmortems/`.

## J — Job queues
- Separate Celery queues: `discovery`, `llm`, `apply`, `email`, `default`; separate concurrency per queue.
- All tasks idempotent; retries with exponential backoff + jitter; dead-letter queue with admin view and "replay".
- Queue depth and task latency exposed as metrics.

## K — KPIs & product analytics
- North-star: **interviews per week**. Supporting: applications/week, callback rate, time-to-first-response, source conversion, resume-variant conversion, ghosting rate.
- Funnel dashboard: discovered → matched → applied → acknowledged → interview → offer.
- Product usage events (digest opened, buttons tapped) via self-hosted PostHog or a simple events table.

## L — LLM ops
- Provider abstraction with primary + fallback provider.
- Prompts versioned as files (`prompts/<name>/v3.md`); version stored with each output.
- Strict JSON schemas; validation + one repair retry; reject on second failure.
- Evaluation set: ~50 labelled jobs; `make eval` scores fit-scoring accuracy and hallucination checks before any prompt change is deployed.
- Track tokens, latency, cost and error rate per call; daily budget with automatic fallback to cheaper model or pause.
- Response caching keyed by (prompt version, input hash).

## M — Metrics & dashboards
- Prometheus metrics from API, workers and connectors (OpenTelemetry SDK).
- Grafana dashboards: System (CPU, memory, disk, containers), Queues, Connectors, Apply engine, LLM, Business funnel.
- Dashboards stored as JSON in repo (`ops/grafana/`), provisioned automatically.

## N — Notifications & alerting
- Alertmanager/Grafana alerts → Telegram (separate ops chat from the job digest).
- Alert rules: service down, error rate spike, queue backlog, connector degraded, LLM budget 80%, disk > 80%, backup failed, home runner offline > 2h, cert expiry.
- Alerts must be actionable: each links to its runbook. No noisy alerts.

## O — Onboarding & UX
- First-run wizard: upload resume → review parsed profile → choose markets/roles → set lanes and caps → connect Telegram and Gmail → preview first matches in dry-run.
- Plain-language explanations for every score ("why this job", "why not eligible").
- Empty, loading and error states designed for every screen.

## P — Privacy & compliance
- Personal data inventory (`docs/privacy/data-map.md`): what is stored, where, why, retention.
- Designed in line with India's DPDP Act and GDPR principles: consent, purpose limitation, minimal data, retention limits, export and delete.
- Encryption at rest for tokens, resumes and emails; TLS everywhere; PII scrubbed from logs and error reports.

## Q — Quality & testing
- Test pyramid: unit (pure logic), integration (testcontainers Postgres/Redis), connector fixture tests, contract tests for API, end-to-end dry-run apply on recorded forms.
- Coverage ≥ 80% on core, normalizer, matching, lifecycle, apply guardrails.
- Load test (Locust or k6) for API and a synthetic 1,000-company discovery run.

## R — Releases & versioning
- Semantic versioning, conventional commits, auto-generated CHANGELOG.
- Database migrations backward-compatible (expand → migrate → contract).
- Public API versioned under `/api/v1`.

## S — Security
- Threat model (`docs/security/threat-model.md`): stolen tokens, leaked resumes, prompt injection via job descriptions/emails, malicious form fields, compromised dependency.
- Prompt-injection defence: job descriptions and emails treated as untrusted data, never as instructions; LLM outputs validated against schemas; LLM never decides to submit on its own.
- OWASP Top 10 checks, rate limiting on API, CORS locked down, security headers, HTTPS via Caddy with automatic certificates.
- Firewall: only 80/443 open; SSH key-only; fail2ban; automatic OS security updates.
- Secrets in environment / Docker secrets, rotated on schedule.

## T — Telemetry: logs & traces
- Structured JSON logs (structlog) with correlation ID across API → queue → worker → external call.
- Centralised logs in Loki; traces with OpenTelemetry → Tempo (or Jaeger).
- Error tracking with Sentry-compatible self-hosted tool (GlitchTip) — grouped errors, release tagging.
- Log retention 14 days; no PII in logs.

## U — Uptime & SLOs
- External uptime checks with Uptime Kuma (API, dashboard, bot heartbeat, home runner heartbeat).
- SLOs: API availability 99.5%; digest delivered by 08:15 IST on 99% of days; inbox events reflected within 20 min for 99%; zero duplicate applications.
- Error-budget view in Grafana.

## V — Vendor & cost management
- Cost dashboard: LLM spend/day, VM resources, storage growth.
- Hard monthly budget; alert at 50/80/100%.
- Vendor abstraction for LLM, email, notifications so any one can be swapped.

## W — Web app & admin console
- User dashboard: pipeline (kanban by state), job detail with score reasoning, documents, interviews, offers, analytics.
- Admin console: connector status, queue + dead letters (replay), feature flags, users, audit log, LLM usage.
- Audit log of every important action (apply submitted, flag changed, data exported/deleted).

## X — eXport & portability
- One-click export of all user data (JSON + CSV + resumes) and full account deletion.
- Import from a spreadsheet of past applications.

## Y — Your feedback loop & support
- In-app and Telegram feedback (`/feedback`), stored with context.
- "Was this match good?" thumbs on each job feeds the evaluation set and ranking.
- Docs site (MkDocs) with user guide, FAQ, architecture, runbooks.

## Z — Zero-downtime deploys & scaling path
- Rolling restarts behind Caddy; workers drain gracefully on shutdown (finish current task).
- Scaling path documented in `docs/architecture.md`:
  1 user → single VM, compose.
  100 users → managed Postgres, more workers, object storage for files.
  1,000+ users → split apply engine and connectors into separate services, autoscaling workers, read replicas.

---

## Resource note for a free VM
Running every tool at once is heavy. Start with a lean ops stack: Prometheus + Grafana + Loki + Uptime Kuma + GlitchTip,
with conservative memory limits per container. Add Tempo tracing, PostHog and Unleash only when the VM has headroom.
Put the ops stack in its own `docker-compose.ops.yml` so it can run separately.

## Where this fits in the phases
- Phase 0: E, H, J (queues), T (logging + correlation IDs), C (CI), Q (test setup), S (basics).
- Phases 1–4: A, D, G, L, F, K (events table).
- Phases 5–6: G fully, I runbooks, P, X.
- Phase 7 (deploy): B, M, N, U, V, Z, S hardening, ops compose.
- Phases 8–9: O, W, Y, R public API, load tests.