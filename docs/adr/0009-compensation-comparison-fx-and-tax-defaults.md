# ADR-0009: Compensation comparison — manual dated FX, USD peg, India new regime default

- **Status:** Accepted
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "PRD review: FX" and "India in-hand estimates"
- **Related:** PRD §4.1, §4.2, US-3.5, US-9.4, R6; ADR-0006

## Context
The owner must compare an annual INR CTC with a monthly AED package. The INR CTC is taxed,
and PF and professional tax are deducted. The AED package has no personal income tax. An FX
API would add a dependency and a terms review, and a wrong or unlabelled rate would mislead.

## Decision
- **v1 FX:** a manual, dated rate in config (`fx.aed_inr`, `fx.as_of`). Every comparison
  shows the rate and its date. A rate older than `fx.max_age_days` (default 30) is flagged.
- **Later automation:** the AED is pegged to the USD at about 3.6725 AED per USD, so
  AED→INR = USD→INR ÷ peg. The peg is a config value (`fx.aed_usd_peg`), not a literal in
  code. Any USD→INR source can then supply the rate.
- **India in-hand:** the **new tax regime** is the default, and the **old regime** is a
  profile option (`india_tax_regime`). Tax slabs, PF rate and professional tax are config
  data with an effective date, not code constants.
- Comparisons never estimate undisclosed figures. Only adjustments the user enters are used.
- Implemented as one `CompensationModel` plug-in per market (ADR-0006).

## Consequences
- Positive: no new dependency, and every assumption is visible.
- Negative: the owner updates the FX rate and the yearly tax data by hand. A stale-rate
  badge and a reminder reduce the risk.
