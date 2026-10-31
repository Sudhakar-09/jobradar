# ADR-0020: Internationalization, RTL and fonts

- **Status:** Accepted
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "Multi-language including RTL"
- **Related:** PRD v0.3 E5, US-5.2, US-11.3; ADR-0014, ADR-0015

## Context
Users and markets span many languages, including right-to-left scripts such as Arabic (the
UAE and other GCC markets). Retrofitting RTL is expensive. It must be designed in from the
first component.

## Decision
- **UI strings:** ICU MessageFormat catalogues in `frontend/packages/i18n`, loaded per locale.
  No user-visible string literals in components (lint rule). Backend user-facing messages
  (notifications, emails, eligibility reasons) use message keys plus parameters, rendered in the
  user's locale.
- **Formatting:** `Intl` APIs for dates, numbers, currencies and relative times, in the user's
  locale and time zone.
- **RTL:** CSS logical properties only (`ms-`/`me-`, `ps-`/`pe-`, `start`/`end`); `dir` set at
  the root from the locale; directional icons mirrored where meaningful; Storybook and visual
  regression run every component in LTR and RTL.
- **Fonts:** **Inter** (variable) as the UI font, with broad Latin, Cyrillic, Greek and
  Vietnamese coverage. **Noto Sans Arabic** (variable) for Arabic script. Further Noto families
  (for example Devanagari) are added per locale. Fonts are self-hosted, subset, preloaded and
  use `font-display: swap`, with metric-compatible fallbacks to avoid layout shift.
- **Documents:** CV rendering supports RTL markets and languages (WeasyPrint with the same font
  stack).

## Consequences
- Positive: new languages are content work, and RTL quality is tested continuously.
- Negative: each locale needs translation review, and the font budget must be watched to keep
  Lighthouse ≥ 90.
