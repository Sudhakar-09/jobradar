# ADR-0001: Modular monolith

- **Status:** Accepted
- **Date:** 2026-10-30 (recorded; agreed earlier in chat)
- **Decision log:** 2026-10-30 — "Architecture"
- **Related:** ADR-0011, ADR-0012, `docs/architecture.md` §2, §3, §8

## Context
The system has one user, one developer and a free or small VM. The product has about ten
domains (profile, connectors, normalizer, matching, documents, apply, lifecycle, notify,
strategy, insights, runner). Their responsibilities are clear, but they share a lot of data
(jobs, applications, profile). PRODUCT_STANDARDS requires a documented path to 1,000+ users.

## Decision
Build **one Python package and one Docker image**, organized as domain modules with strict
boundaries. Run it as several **process roles**: api, bot, beat, one worker per queue, and
dashboard. Domains talk through service interfaces. They never use each other's tables or
repositories.

## Consequences
- Positive: one deploy, one migration history, in-process calls, and easy refactoring and
  testing. It fits a small VM.
- Positive: process roles already separate the noisy parts (Playwright apply, LLM,
  discovery), so they can be scaled or split later without a rewrite.
- Negative: boundaries erode easily. Import-linter contracts in CI guard against this
  (ADR-0012).
- Follow-up: at about 1,000 users, extract `apply` and `connectors` into separately deployed
  services that keep the same interfaces (`docs/architecture.md` §8).

## Alternatives considered
- **Microservices from day one:** far more operational cost than one user needs, plus
  distributed transactions for application state.
- **Single unstructured app:** fastest start, but it would be hard to keep the scaling path
  and the safety guarantees (apply guards in one place).
