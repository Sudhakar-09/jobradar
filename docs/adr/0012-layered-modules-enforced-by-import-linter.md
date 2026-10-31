# ADR-0012: Layering api → services → repositories → models, enforced by import-linter

- **Status:** Accepted (Step 2 review, 2026-10-30; import-linter approved as a dev dependency).
  Enforcement is configured in Step 5.
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "Step 2 review"
- **Related:** ADR-0001; `docs/architecture.md` §3.1; `docs/coding-standards.md`

## Context
A modular monolith keeps its value only if its boundaries hold. The safety guarantees
(per-user isolation, apply guards, audit logging) must live in one layer that every entry
point passes through.

## Decision
- Imports flow one way: entry points (`api`, `tasks`, `cli`, bot handlers) → **services** →
  **repositories** → **models**. Every layer may import `core`, and `core` imports no domain.
- A domain calls another domain only through that domain's service interface, exported in
  `<domain>/__init__.py`.
- Only repositories issue SQL, and every query on user-owned data takes `user_id`.
- **import-linter** contracts enforce this in pre-commit and CI. The owner approved it as a
  dev dependency on 2026-10-30.

## Consequences
- Positive: boundary violations fail CI, and authorization and audit live in one place.
- Negative: some boilerplate, such as thin services for simple reads.
