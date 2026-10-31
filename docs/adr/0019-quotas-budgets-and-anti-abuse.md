# ADR-0019: Quotas, LLM budgets, plans and anti-abuse

- **Status:** Accepted
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "Usage limits, budgets and anti-abuse"
- **Related:** PRD v0.3 §7.1–§7.2, US-3.6, US-10.5, US-10.6; PRODUCT_STANDARDS G, V; `docs/architecture.md` §8

## Context
With many users, LLM cost grows with users × jobs, and an automation tool can be misused to
flood employers. Both must be controlled on the server side, where they can't be bypassed.

## Decision
- **Plans as config** (`free`, `supporter`, `friends_beta`, …) set per-user limits. **Global
  ceilings** (config) can never be raised by a plan or a user. Billing is out of scope.
- **Metrics:** automated and assisted applications per day, applications per employer per
  30 days, tailored documents per day, LLM tokens per day and cost per month, alerts ingested per
  day, storage.
- **Enforcement point:** `quotas.check` → anti-abuse rules → action → `quotas.consume` → audit,
  inside services. Redis holds hot counters and Postgres holds the authoritative rollups. Apply
  metrics **fail closed** when counters are unavailable.
- **Anti-abuse rules:** eligibility required; fit score ≥ max(user minimum, global floor);
  per-employer cap; no duplicates per (user, job) and (user, employer, title); live automation
  opt-in per lane after a dry-run review; cool-down on high rejection-without-response rates,
  bursts or employer reports; admin suspension; public abuse contact.
- **LLM budget:** the gateway pre-checks the estimated cost and records actual usage. When a
  user's budget runs out, the system degrades in this order: tailoring → rules-only scoring →
  digest still delivered. Shared normalization is billed to `system`.

## Consequences
- Positive: predictable cost per user, and the product can't become a spam cannon.
- Negative: users may hit limits, so the UI shows usage meters and reset times.
