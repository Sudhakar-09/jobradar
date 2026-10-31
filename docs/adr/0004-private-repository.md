# ADR-0004: Private repository

- **Status:** Accepted
- **Date:** 2026-10-30 (recorded)
- **Decision log:** 2026-10-30 — "Repository visibility"
- **Related:** CLAUDE.md rule 5, §11; PRODUCT_STANDARDS P, S

## Context
The repo holds personal configuration examples, strategy and operational details. A leaked
real profile or credential would be serious, even though the rules already forbid
committing them.

## Decision
The GitHub repository is **private**. This is defence in depth and **does not replace** the
rules: no secrets, personal data or real resumes are committed (only `*.example.*` files),
and secret scanning (gitleaks) still runs in CI.

## Consequences
- Positive: less exposure if a mistake slips through.
- Negative: no public contributions, and GitHub Actions minutes come from the private quota.

## Alternatives considered
- **Public repo:** possible later after a data audit. It would need a fully scrubbed history.
