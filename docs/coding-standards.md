# JobRadar — Coding standards

| | |
|---|---|
| Status | Draft for owner review |
| Version | 0.1 (2026-10-30) |
| Applies to | All code in this repository: `src/`, `tests/`, `alembic/`, `scripts/` (except `scripts/archive/`), and `frontend/` from Phase 4 |
| Related | `CLAUDE.md` (rules, workflow), `docs/PRODUCT_STANDARDS.md` (quality bar), ADR-0012 (layering), `docs/lld/README.md` (shared types, canonical identifiers) |

**Principle: if a rule matters, a tool enforces it.** Every rule below says how it is enforced.
"Review" means the PR checklist (`.github/pull_request_template.md`) and the self-review step in
`CLAUDE.md`. Tool configuration lives in `pyproject.toml`, `.pre-commit-config.yaml` and
`.github/workflows/ci.yml`. Changing a rule means changing this file **and** the tool config in
the same PR, with a `docs/decisions-log.md` entry.

## 0. Enforcement map

| Rule | Tool | Where it runs |
|---|---|---|
| Formatting | `ruff format` | pre-commit, CI `quality` |
| Lint: complexity ≤ 10, docstrings, naming, security, async, datetime, magic values, banned APIs | `ruff check` (rule set in `pyproject.toml`) | pre-commit, CI `quality` |
| Types: strict on all of `src/` | `mypy` (`strict = true`, pydantic plugin) | pre-commit, CI `quality` |
| Layering: entry points → domains → models → core; repositories private to their service | `import-linter` (3 contracts) | pre-commit, CI `quality` |
| No hardcoded URLs, no PII in log calls, no debugger calls | pre-commit `pygrep` hooks | pre-commit, CI `quality` |
| Tests pass | `pytest --strict-markers` | pre-commit (fast suite), CI `tests` (all but integration until Phase 2) |
| Coverage ≥ 80 % overall and on critical packages | `pytest-cov` + `coverage report` | CI `tests` |
| Supply chain: actions pinned to full commit SHAs; weekly dependency updates | Workflow review; Dependabot (`.github/dependabot.yml`) | CI config, Dependabot PRs |
| API contract valid | `openapi-spec-validator` | CI `contract` (drift check from Phase 4) |
| Vulnerable dependencies, leaked secrets | `pip-audit`, `gitleaks` | CI `security` |
| Conventional commits | `commit-msg` hook; PR title check | local hook, CI `pr-title` |
| PR checklist | PR template | review |

Set up a clone once: `uv sync --group dev && uv run pre-commit install`. Run everything
locally with `uv run pre-commit run --all-files`.

## 1. Project structure

```
src/jobradar/
├── core/            settings, db session, logging, errors, scope, clock, ids, http, llm,
│                    queue (Celery app), flags, plugins, packs — imports no domain
├── models/          SQLAlchemy tables only (one module per domain: models/jobs.py, …)
├── <domain>/        accounts, privacy, quotas, profile, connectors, normalizer, matching,
│   │                documents, apply, lifecycle, notify, strategy, insights, runner, admin
│   ├── __init__.py  the public interface: re-exports the service functions and DTOs other
│   │                modules may use (and nothing else)
│   ├── service.py   public service functions (or service/ package for large domains)
│   ├── repository.py  SQL for this domain's tables; takes UserScope; private to service
│   ├── schemas.py   Pydantic DTOs at the module boundary
│   ├── rules.py     pure functions (no I/O): rules, scoring, guards, conversions
│   └── plugins/     registered plug-ins (connectors, parsers, compensation models, …)
├── api/             FastAPI app and routers (api/routers/<domain>.py) — thin
├── tasks/           Celery tasks (tasks/<domain>.py) — thin; celery_app entry point
└── cli.py           CLI — thin
```

A domain package grows these files as it needs them; it never creates empty modules ahead of
time (same principle as the incremental schema, `docs/lld/database.md` §9).

## 2. Layering (ADR-0012)

| Rule | Enforced by |
|---|---|
| Entry points (`api`, `tasks`, `cli`) call **services only** | import-linter: "Entry points never touch repositories or models directly" |
| Layers: entry points → domains → `models` → `core`; never upwards | import-linter: "Entry points > domains > models > core" |
| A domain's repository is used only by that domain's service | import-linter: "Only a domain's own service may use its repository" |
| A domain calls another domain only through `<other_domain>/__init__.py` exports | Review; LLD public interfaces are the allow-list |
| Only repositories issue SQL; every user-owned query takes `UserScope` | Review + isolation tests (§10) + Postgres RLS |
| `core` imports no domain | import-linter (layers) |

Domains not created yet are listed as optional layers in `pyproject.toml` (in parentheses).
**When you create a domain package, remove its parentheses in the same PR**, so the contract
cannot silently skip it.

## 3. Naming

| Thing | Convention | Example |
|---|---|---|
| Packages, modules | `snake_case`, singular domain nouns | `jobradar.matching.rules` |
| Classes, Pydantic models | `PascalCase`; DTO suffixes: `…Request`, `…View`, `…Result`, `…Plan` | `RankedJob`, `AssistPlan` |
| Functions, methods, variables | `snake_case`; verbs for functions | `score_new`, `top_matches` |
| Constants | `UPPER_SNAKE_CASE`, annotated `Final` | `MARKET_PACK_STALE_AFTER: Final = timedelta(days=90)` |
| Private helpers | leading `_` | `_parse_years` |
| Booleans | `is_`/`has_`/`can_`/`should_` prefixes | `is_eligible` |
| Exceptions | `…Error`, subclass of `JobRadarError` | `GuardFailedError` |
| Enums | `StrEnum`, singular name, lower-case values | `ApplicationState.MATCHED = "matched"` |
| Database | as `docs/lld/database.md` §1 | `job_scores`, `ix_jobs_country_status_last_seen_at` |
| API paths and JSON | `snake_case` JSON, kebab-free plural paths, `{resource_id}` params | `/applications/{application_id}/history` |
| Log events | `<module>.<event>`, past-tense or noun phrase | `connectors.run_finished` |
| Metrics | `jobradar_<module>_<name>_<unit>` (`_total`, `_seconds`, `_bytes`) | `jobradar_connectors_jobs_found_total` |
| Flags, quota metrics, consent sources, events | exactly as listed in `docs/lld/README.md` → Canonical identifiers | `apply.live_submit.enabled` |
| Tests | `test_<unit>_<condition>_<expected>` | `test_transition_from_applied_to_matched_is_invalid` |
| Branches | `<type>/<short-topic>` | `feat/greenhouse-connector` |

Naming of Python code is enforced by ruff `N`; the rest by review and the canonical identifier
list.

## 4. Types and docstrings

- **mypy strict on all of `src/`** (`pyproject.toml`), with the pydantic plugin. `Any` is allowed
  only at true boundaries (raw JSON from a source before validation) and must be narrowed
  immediately with a Pydantic model.
- Pydantic v2 models at every module boundary (service inputs/outputs, task payloads, API
  bodies). Request models use `extra="forbid"`.
- `# type: ignore[code]  # reason` only with an error code and a reason (mypy
  `ignore-without-code`, ruff `PGH003`). Bare ignores fail CI.
- **Google-style docstrings** (ruff `D`, `convention = "google"`) on every public module, class,
  function and method in `src/`. Tests are exempt. Example:

```python
async def top_matches(scope: UserScope, *, limit: int, since: datetime | None = None) -> list[RankedJob]:
    """Return the user's highest-ranked eligible matches.

    Args:
        scope: Caller's tenant scope.
        limit: Maximum number of jobs to return.
        since: Only jobs first seen after this instant, if given.

    Returns:
        Ranked jobs, best first.

    Raises:
        BudgetExceededError: The user's LLM budget is exhausted and no cached scores exist.
    """
```

## 5. Errors

- All domain errors subclass **`JobRadarError`** (`core/errors.py`; hierarchy in
  `docs/lld/README.md`). Each has a stable `code` that maps to an API problem type
  (`docs/api.md` §4) and a message key for users.
- Never `raise Exception(...)` or another builtin for domain failures (ruff `TRY002`). Use
  `ValueError`/`TypeError` only for programming errors.
- **No bare `except:`** (ruff `E722`) and **no blind `except Exception`** (ruff `BLE001`), except
  at the outermost boundary (API exception handler, task wrapper, health checks), where the
  exception is logged with `logger.exception` and converted, never swallowed silently.
- Catch the narrowest exception; re-raise with `raise NewError(...) from exc` (ruff `B904`).
- External failures become `ExternalServiceError` with `retryable=True|False`. Only retryable
  errors are retried (tenacity in `core/http`, Celery `autoretry_for` in tasks).
- `# noqa: CODE -- reason` is the only accepted suppression form. A suppression without a reason
  fails review.

## 6. Async, I/O and timeouts

- **Every I/O call has a timeout.** Defaults live in settings, never in code. Each setting is
  added together with the first code that performs that kind of I/O (no settings ahead of time);
  the values below are the agreed defaults:

| I/O | Mechanism | Default (settings) |
|---|---|---|
| HTTP (connectors, providers) | shared `httpx.AsyncClient` from `core.http` only (ruff `TID251` bans constructing clients elsewhere) | connect 5 s, read 20 s, total 30 s |
| PostgreSQL | `statement_timeout`, `lock_timeout`, `connect_timeout` per connection | 15 s / 5 s / 5 s |
| Redis | socket connect/read timeouts | 2 s |
| LLM calls | `LlmGateway(timeout_s=…)` per model tier | small 20 s, standard 45 s, premium 90 s |
| Playwright | navigation and action timeouts | 30 s / 10 s |
| Celery tasks | soft/hard time limits per queue | `docs/architecture.md` §7 |
| Gmail / mail providers | client timeouts via `core.http` | 20 s |

- **No blocking calls in async code** (ruff `ASYNC`): no `time.sleep`, sync HTTP, sync file I/O
  on large files or sync DB drivers inside `async def`. Wrap unavoidable sync libraries with
  `anyio.to_thread.run_sync`.
- Services that touch the database are `async def` (SQLAlchemy async session). Pure rule
  functions are sync.
- Datetimes are timezone-aware UTC (ruff `DTZ`); "now" comes from the injected `Clock`, never
  `datetime.now()` inside domain logic, so tests can control time.
- Retries: exponential backoff with jitter, bounded attempts, only for retryable errors. Apply
  submission is **never** retried after the submit click (`docs/lld/apply.md`).

## 7. Configuration, magic numbers and URLs

| Kind of value | Where it lives |
|---|---|
| Secrets, hosts, ports, provider keys, timeouts, budgets | pydantic-settings (`core/settings.py`), validated at startup; documented in `.env.example` |
| Market, role, persona knowledge | packs (`packs/`) |
| Per-source rules, rate limits, URLs of public APIs | `config/source_policies.yaml`, `config/connectors.yaml` |
| Runtime switches | flags (`settings_flags`), canonical keys only |
| Tax tables, FX, consent texts | dated config files (`config/compensation/`, settings `fx.*`, `config/consents/`) |
| True constants of the code (e.g. a protocol limit) | module-level `UPPER_SNAKE: Final` with a comment saying why |

- **No magic numbers:** ruff `PLR2004` catches magic comparisons; review catches the rest. A
  bare literal other than `0`, `1`, `-1` or an obvious unit in business logic needs a named
  constant or a setting.
- **No hardcoded URLs** in `src/`: pre-commit `no-hardcoded-urls` (anything matching
  `scheme://`) fails outside `core/settings.py`.

## 8. Logging

- `structlog` only: `logger = structlog.get_logger(__name__)` (ruff bans `logging.getLogger`
  outside `core/logging.py`). JSON output, UTC ISO timestamps.
- **Event names** `<module>.<event>`; context as key/value fields, never formatted into the
  message (ruff `G`).
- Always bound (by middleware/task wrapper): `correlation_id`, `user_id` (opaque UUID), `task`
  or `route`. Never log request/response bodies.
- **No PII, ever:** no email, phone, names, addresses, dates of birth, nationality, salary
  figures, resume or email text, tokens, passwords, cookies, or untrusted third-party text.
  Enforced by the `no-pii-in-logs` hook (blocks known PII keys in log calls), a structlog
  processor that drops a deny-list of keys (`core/logging.py`, Phase 2), and a test that scans
  captured logs from the synthetic-user suite for planted PII markers.
- Levels: `debug` local only; `info` business events; `warning` degraded but handled;
  `error` failed operation needing attention; `exception` only inside `except`.

## 9. Security in code

- Untrusted text (job descriptions, emails, page content, form labels) is typed
  `Untrusted[str]`, passed to the LLM only as a data variable, rendered as text (never HTML), and
  never logged.
- SQL only through SQLAlchemy with bound parameters; no string-built SQL (ruff `S608`).
- `yaml.safe_load` only (ruff `S506`); no `pickle` (banned), no `eval`/`exec` (ruff `S307`),
  no shell execution (banned `os.system`; ruff `S602`–`S607`).
- Secrets only from settings; never in code, tests, fixtures or logs (gitleaks in CI).
- Crypto: argon2id for passwords, AES-GCM via `core.crypto` for `_enc` columns, `secrets` for
  tokens (ruff `S311` bans `random` for security).

## 10. Database code

- Repositories take `UserScope` as their first parameter for user-owned data; the session sets
  `app.user_id` per transaction (RLS, `docs/lld/database.md` §4).
- No N+1 queries: load related rows explicitly (`selectinload`) or with one query.
- Migrations follow `docs/lld/database.md` §7 (expand → migrate → contract, downgrade, RLS in the
  same migration, `lock_timeout`, concurrent indexes) and §9 (tables only in their phase).
- Every new user-owned table and every endpoint that takes a resource ID gets an isolation test
  (`@pytest.mark.isolation`).

## 11. API code

- Routers are thin: authenticate, validate, build `UserScope`, call **one** service function, map
  the result. No business logic, no repository or model imports (import-linter).
- Request/response models come from the owning domain's `schemas.py` and match
  `docs/openapi.yaml`. Contract changes need a PR with the reason (`docs/api.md` §10).
- Errors are raised as `JobRadarError` subclasses and mapped to problem details by one exception
  handler.

## 12. Tests

| Kind | Marker | Location | Rules |
|---|---|---|---|
| Unit | `unit` (default) | `tests/unit/<module>/` | Pure logic; no network, DB or sleeping; fast |
| Integration | `integration` | `tests/integration/` | Real PostgreSQL/Redis (compose or testcontainers); each test in a rolled-back transaction |
| Connector fixtures, golden data | `golden` | `tests/golden/<market>/`, `tests/fixtures/<connector>/` | Saved responses only; never live sites (CLAUDE.md rule 8) |
| Conformance | `conformance` | `tests/conformance/` | Parametrized over every pack |
| Synthetic users | `synthetic` | `tests/synthetic/` | End-to-end dry-run with recorded LLM responses |
| API contract | `contract` | `tests/contract/` | Against `docs/openapi.yaml` |
| Isolation | `isolation` | `tests/isolation/` | User B never sees user A's data |

- Markers are declared in `pyproject.toml`; `--strict-markers` rejects unknown ones.
- Naming: `test_<unit>_<condition>_<expected>`. One behaviour per test; Arrange–Act–Assert.
- Time comes from an injected `Clock`; IDs from an injected generator where order matters.
- No real network: HTTP is served from saved fixtures through `httpx.MockTransport` injected into
  the `core.http` client (no extra dependency); LLM calls use recordings keyed by (prompt version,
  input hash).
- The Phase 0–1 tests live flat in `tests/`; they move into the layout above when their module is
  next changed (no big-bang move).
- Test data is synthetic; never real personal data (CLAUDE.md §11).
- **Coverage gates (CI, branch coverage via `pytest-cov`):** ≥ 80 % overall (`fail_under` in
  `pyproject.toml`) and ≥ 80 % on `core`, `normalizer`, `matching`, `lifecycle` and `apply`
  (PRODUCT_STANDARDS Q). Locally: `uv run pytest --cov` then `uv run coverage report`.

## 13. Frontend (enforced from Phase 4, when `frontend/` exists)

- TypeScript `strict`, no `any` (ESLint `@typescript-eslint/no-explicit-any`), no non-null
  assertions without a comment.
- Design tokens only: lint fails on raw colours, sizes, durations and arbitrary Tailwind values
  outside `packages/tokens` (ADR-0015).
- No user-visible string literals in components: ICU message keys only (ADR-0020); logical CSS
  properties only (RTL).
- Components are built and reviewed in Storybook first (light/dark, LTR/RTL, all states);
  screens compose only `packages/ui` components.
- Accessibility: axe in component tests; WCAG 2.2 AA; Lighthouse CI ≥ 90 (perf, a11y, best
  practices).
- Server state only through TanStack Query hooks generated around `packages/api-client`.
- The exact ESLint/Stylelint/Prettier configuration is set up in Phase 4 and added to this file.

## 14. Git, commits and pull requests

- **Conventional Commits** (`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`,
  `ci`, `chore`, `revert`; optional scope; `!` for breaking). Enforced by the `commit-msg` hook
  locally and the PR title check in CI (PRs are squash-merged, so the title becomes the commit).
- Scope is the module or area: `feat(matching): …`, `docs(lld): …`, `ci: …`.
- Small PRs, one story or one concern. The PR template checklist is completed honestly; unticked
  items are explained.
- Commit message footer for AI-assisted commits follows the attribution instructions in effect.
- Every task ends with `docs/progress.md` (and `docs/decisions-log.md` if a decision was made)
  updated, committed and pushed (CLAUDE.md rule 9).

## 15. Exceptions to these standards

A rule may be broken only locally, visibly and with a reason:
- `# noqa: CODE -- reason` or `# type: ignore[code]  # reason` on the single line.
- A broader exception (per-file ignore, contract exclusion) needs a `docs/decisions-log.md`
  entry and a comment next to the config line.

Current per-file exceptions (all in `pyproject.toml`): tests may use `assert`, magic values and
fake credentials (S105/S106), and skip docstrings/annotations; `alembic/` skips docstrings; `cli.py` may `print`; `core/logging.py`
and `core/http.py` may use the APIs banned elsewhere; `scripts/archive/` is excluded entirely;
`docs/` is excluded from `ruff format` (its Python blocks are design illustrations, and ruff ≥ 0.17
formats code blocks inside Markdown).
