# ADR-0005: Checkout at C:\dev\jobradar, outside OneDrive

- **Status:** Accepted
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "Project location"
- **Related:** `docs/progress.md` (relocation notes)

## Context
The first checkout was inside a folder synced by OneDrive. Syncing `.venv`, `.git` and Docker
volumes causes file locks, slow installs and corruption from partial syncs. It also copies
the project, including any local `.env`, into a cloud sync service.

## Decision
The active checkout is **`C:\dev\jobradar`**. The OneDrive copy is kept only as a backup and
must not be used. Environments are recreated with `uv sync --link-mode=copy`.

## Consequences
- Positive: tooling works reliably, and `.env` stays out of cloud sync.
- Negative: the OneDrive copy may drift and must be ignored. The owner can delete it later.
