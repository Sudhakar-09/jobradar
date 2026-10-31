# ADR-0015: Design system, tokens and visual quality gates

- **Status:** Accepted
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "Premium UI: design system first"
- **Related:** PRD v0.3 §6 (E1–E10); ADR-0014, ADR-0020; `docs/design-system.md` (Step 6)

## Context
A premium feel comes from consistency: one colour system, one type scale, one motion language,
and every state designed. Without enforcement, components drift into hardcoded values and
one-off styles.

## Decision
- **Tokens are the only source of visual values:** colour (primitives → semantic roles, light
  and dark), typography, spacing, radius, elevation, motion (durations 150–300 ms, named easing
  curves), z-index and breakpoints (360 px → large desktop). They are emitted as CSS variables
  plus a Tailwind preset from `frontend/packages/tokens`.
- **No hardcoded colours, sizes or durations** in components. A lint rule (ESLint plus a
  Tailwind class check) fails CI on raw values and arbitrary-value classes outside the tokens
  package.
- **Contrast:** every semantic text/background pair is checked against WCAG AA in a unit test
  over the token tables, for both themes.
- **Design system first:** every component is built in Storybook with light/dark, all states,
  and LTR/RTL stories before any screen uses it. Screens compose only `packages/ui` components.
- **Quality gates in CI:** Playwright visual regression over Storybook stories and key screens;
  Lighthouse CI budgets ≥ 90 for performance, accessibility and best practices; axe checks in
  component tests; CLS < 0.1.
- **Motion:** shared Motion presets; `prefers-reduced-motion` turns animations into instant
  state changes; skeletons instead of spinners for content.

## Consequences
- Positive: consistent premium look, safe theming, and accessible by construction.
- Negative: slower first screens, because the design system comes first. Visual baselines need
  maintenance.
