# ADR-0013: Product for everyone; staged rollout

- **Status:** Accepted
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "Scope change: a product for everyone"
- **Amends:** ADR-0006 (India + UAE become the first configuration, not the scope)
- **Related:** PRD v0.3 §1–§4, §8; ADR-0017 … ADR-0022

## Context
JobRadar was scoped as a personal tool for one India-based Java backend engineer targeting
India and the UAE. The owner wants a product that works for anyone: any role, any country,
any seniority, in tech and non-tech fields. That includes students, returners, movers,
freelancers and executives.

## Decision
- JobRadar is a **product for everyone**. User #1's profile (India + UAE, Java backend) is the
  **first configuration**.
- **Strategy: design for everyone, launch with one user, then friends (invite-only), then the
  public.** The stages map to PRD phases: Stage 1 = Phases 2–7, Stage 2 = Phases 8–10,
  Stage 3 = Phase 11.
- Everything that varies by country, field, role, persona, language or source is **config or a
  registered plug-in**. Adding a country or role must need no core code changes, and a CI golden
  test proves this for every pack.
- All code is multi-tenant-correct from now on (ADR-0017), even while only one user exists.

## Consequences
- Positive: packs and plug-ins keep the core small, and each new market or field is mostly
  content work.
- Negative: more upfront design (auth, tenancy, quotas, consent, i18n). Stage gates and "build
  for one" keep the implementation small until each stage needs it.
- Follow-ups: extend pack schemas (US-1.2 AC2/AC3); add `CLAUDE.md` phases 10–11 in Step 7.

## Alternatives considered
- **Stay single-user, generalize later:** cheaper now, but retrofitting tenancy, consent and
  i18n is costly and risky.
