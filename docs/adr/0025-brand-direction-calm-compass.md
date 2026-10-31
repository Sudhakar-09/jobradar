# ADR-0025: Brand direction "Calm Compass" with celebration from "Bright Momentum"

- **Status:** Accepted
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "Brand direction"
- **Related:** PRD v0.4 §6 (E1–E10); ADR-0014, ADR-0015, ADR-0020; `docs/design-system.md`,
  `docs/ux.md`, `docs/design/brand-directions.html`

## Context
Three brand directions were previewed side by side with the same components (Step 6):
A "Calm Compass" (teal, Inter, gentle motion), B "Bright Momentum" (indigo/coral, Geist, springy
motion) and C "Quiet Confidence" (ink/paper, serif headings, crisp motion). The product serves
stressed job seekers in every field and country.

## Decision
- **Direction A — Calm Compass** is the brand: teal primary, warm amber accent, calm neutrals,
  Inter + Noto Sans Arabic (unchanged from ADR-0020), radius 8/10/14 px, gentle motion
  (160–320 ms, ease-out, no bounce).
- **Exception:** Direction B's **celebration animation** (spring easing with slight overshoot,
  confetti burst, ≤ 1.2 s) is used **only** for interview and offer events, once per event, and
  replaced by a static banner under reduced motion. Everything else keeps A's gentle motion.
- Tokens, components and screens are specified in `docs/design-system.md` and `docs/ux.md`.

## Consequences
- Positive: a calm, trustworthy base for anxious users, plus a memorable moment where it matters
  (outcomes, not activity). No change to the font decision.
- Negative: two easing families must be kept apart. The celebration preset is the only consumer
  of `--ease-celebrate`, which a lint rule checks.
