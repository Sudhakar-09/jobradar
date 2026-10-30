# JobRadar

JobRadar is a self-hosted job search operating system. Phase 0 provides the Python environment,
PostgreSQL and Redis services, structured logging, migrations, and liveness/readiness endpoints.
See [the product standards](docs/PRODUCT_STANDARDS.md) for the product-wide design requirements.

## Phase 0 setup

Requirements: Windows 11, Python 3.12, uv, Git, Docker Desktop with WSL2, and VS Code.

From PowerShell in the repository root:

```powershell
uv sync --group dev
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d
$env:PYTHONPATH = "src"
uv run alembic upgrade head
uv run ruff check .
uv run mypy src
uv run pytest
uv run uvicorn jobradar.api.app:app --host 127.0.0.1 --port 8000
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