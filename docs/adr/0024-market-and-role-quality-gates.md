# ADR-0024: Market and role quality gates, synthetic users and rollout flags

- **Status:** Accepted
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "Multi-market and multi-role testing"
- **Related:** PRD v0.4 §8a, US-2.9, US-3.8, US-4.7, US-10.10; `docs/architecture.md` §13a;
  ADR-0013, ADR-0021

## Context
India and the UAE are only the first launch markets. "Adding a country or role needs no core
code" (G9) is only true if every pack is held to the same, automated quality bar. Shipping a
market with wrong salary conventions, visa rules or broken parsers would harm users directly.

## Decision
- **Pack conformance suite:** a parametrized test suite that every market, role and persona pack
  must pass. It covers schema, currency, language/RTL, CV format, visa rules, salary conversion,
  eligibility and source parsing.
- **Golden datasets per market:** synthetic or anonymized postings and alert emails with expected
  normalized output. Any diff fails CI until the expected file is updated deliberately.
- **Synthetic test profiles:** fictional users covering personas, fields, seniorities and
  countries (`syn-01` … `syn-10` to start), run end to end in dry-run in CI. LLM calls are
  replaced by **recorded responses** keyed by (prompt version, input hash), so CI is
  deterministic and free.
- **UI matrix:** every supported locale and direction, currency and date format, at phone and
  desktop sizes, in light and dark themes. A smoke subset runs on each PR and the full matrix
  nightly.
- **Rollout flags:** `market.<code>.enabled` and `role.<code>.enabled`. The flag service refuses
  to enable one unless conformance is green on `main`. Each market has a checklist in
  `docs/markets/<code>.md`: pack verified, sources connected, conformance green, synthetic users
  passing, golden data green, native-speaker translation review, UI matrix green, owner sign-off.
- **Priority order after India + UAE:** Saudi Arabia, Qatar, UK, US, Canada, Germany,
  Singapore, Australia, Remote. Reviewed quarterly against demand.

## Consequences
- Positive: G9 is proven by tests, regressions in one market can't slip in through changes for
  another, and the order of new markets is clear.
- Negative: more CI time (the full UI matrix runs nightly only). Golden data and recordings
  need care when prompts change. Native-speaker reviews take time per language.
