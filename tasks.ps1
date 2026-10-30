param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('dev', 'test', 'lint', 'typecheck', 'migrate', 'up', 'down', 'api')]
    [string]$Task
)

$ErrorActionPreference = 'Stop'

switch ($Task) {
    'dev' { uv sync --group dev }
    'test' { uv run pytest }
    'lint' { uv run ruff check . }
    'typecheck' { uv run mypy src }
    'migrate' { uv run alembic upgrade head }
    'up' { docker compose up -d }
    'down' { docker compose down }
    'api' { uv run uvicorn jobradar.api.app:app --host 127.0.0.1 --port 8000 }
}

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
