# ADR-0006: Pluggable markets; India + UAE, Java Backend first

- **Status:** Accepted; **amended by ADR-0013**. India + UAE / Java Backend is the first
  configuration (user #1), not the product scope. The pluggability decision below still applies.
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "Target market and role"
- **Related:** PRD §4, G9; `docs/architecture.md` §3.3; ADR-0009, ADR-0010

## Context
The owner targets India and the UAE for Java Backend roles. The two markets differ in:
- compensation conventions: annual INR CTC vs monthly AED with no income tax
- work authorization: UAE roles need employer sponsorship
- channels: Gulf job boards
- CV conventions

More markets may follow, such as other GCC countries, the UK or Germany.

## Decision
India and the UAE are the **active** markets and `java_backend` is the active role. All
market-specific behaviour comes from **market packs** (validated YAML) and **registered
plug-ins** (`CompensationModel`, `EligibilityRule`, `AlertEmailParser`, `CvFormatter`,
sponsor-register loader). Core code contains no branches on market names.

## Consequences
- Positive: adding a market means a pack, config and optional plug-ins, with no migration.
- Negative: plug-in registries add some indirection, and each registered plug-in needs its
  own tests.
- Follow-up: at Phase 2 start, extend the `MarketPack` schema with channel access modes, CV
  field defaults and a compensation model ID, and add Naukrigulf to the UAE pack.

## Alternatives considered
- **Hard-coding India and UAE logic:** quicker now, but it blocks G9 and spreads conditionals
  through the code.
