# JobRadar

JobRadar is a self-hosted job search operating system. Phase 0 provides the development scaffold;
Phase 1 adds validated profile, answer-bank, and pack loading, plus conservative plain-text resume
parsing.
See [the product standards](docs/PRODUCT_STANDARDS.md) for the product-wide design requirements.

## Phase 1 — Profile and packs

The committed profile and answer-bank files are generic examples. Copy them to the ignored local
configuration paths before adding personal information:

```powershell
Copy-Item .\config\profile.example.yaml .\config\profile.yaml
Copy-Item .\config\answer_bank.example.yaml .\config\answer_bank.yaml
```

The profile loader rejects unknown fields. `salary_expectations` is keyed by currency, with
optional `minimum` and `maximum` values; leave unknown facts unset. Answer-bank entries require a
canonical question and a user-provided answer.

Validate and display the example profile, or supply a local profile explicitly:

```powershell
uv run jobradar profile show
uv run jobradar profile show --profile .\config\profile.yaml
```

The market and role packs in `packs\` are validated with strict Pydantic schemas. The current
target packs cover India, UAE, and Java Backend. Market packs without a `last_verified` date, or
with a date older than 90 days, produce a warning.

`jobradar profile parse-resume <path>` accepts a UTF-8 plain-text file and extracts only explicitly
labeled fields (such as `Name:`, `Skills:`, and `Years of Experience:`). It does not infer missing
facts; unsupported or ambiguous values are left unset or reported as errors. Review its output
before saving it as a profile.

## Phase 0 setup

Requirements: Windows 11, Python 3.12, uv, Git, Docker Desktop with WSL2, and VS Code.

From PowerShell in the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tasks.ps1 dev
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tasks.ps1 up
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tasks.ps1 migrate
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tasks.ps1 lint
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tasks.ps1 typecheck
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tasks.ps1 test
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tasks.ps1 api
```

In a second PowerShell window, check the API with:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/ready
```

`/health` reports process liveness. `/ready` checks PostgreSQL, Redis, and the Celery broker and
returns HTTP 503 when a dependency is unavailable. The Compose password default is for local
development only; use a private `.env` for local overrides and never commit real credentials.

Run the configured checks with `uv run ruff check .`, `uv run mypy src`, and `uv run pytest`.
Run `uv run pre-commit run --all-files` and install repository hooks with
`uv run pre-commit install`.

The PowerShell task runner supports `dev`, `test`, `lint`, `typecheck`, `migrate`, `up`, `down`,
and `api`. The application package is installed by `uv sync`, so no `PYTHONPATH` override is
needed. To launch the API directly, run `uv run uvicorn jobradar.api.app:app`.
If PowerShell blocks local scripts, invoke a task with a process-scoped policy override, for example
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tasks.ps1 lint`; this does not change the
persistent execution policy.

## Phase 0 standards review

- E — Partial: typed settings load from environment or `.env`, and every setting is documented in
	`.env.example`. Separate staging/production configuration is later work.
- H — Partial: `/health` is a liveness check; `/ready` checks PostgreSQL, Redis, and the queue
	broker; Compose dependencies have healthchecks and restart policies. API/worker Compose services
	and worker recovery are later work.
- J — Partial: named Celery queues and broker readiness are configured. Task idempotency, retries,
	dead-letter handling, and queue workers are deferred until task implementations.
- T — Partial: JSON logs include a request correlation ID. Cross-worker/external-call propagation,
	centralized logs, traces, and error tracking are deferred.
- C — Partial: GitHub Actions runs Ruff, mypy, and pytest. Coverage gates, image/security scans,
	image publishing, and deployment are deferred.
- Q — Partial: unit tests cover settings and health behavior. Integration containers, connector
	fixtures, contract/end-to-end/load tests, and coverage targets belong to later phases.
- S — Partial: local secrets/config and personal files are ignored, and JSON-only logging avoids
	request bodies. Threat modeling, API hardening, TLS, and operational security are deferred.