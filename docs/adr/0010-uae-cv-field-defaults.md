# ADR-0010: UAE CV field defaults with per-application toggle

- **Status:** Accepted
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "PRD review: UAE CV"
- **Related:** PRD §4.2, US-5.1 AC3; ADR-0006; PRODUCT_STANDARDS P

## Context
Gulf CVs often include nationality, location, visa status and availability. Some also
include a photo, date of birth and marital status. Those last three are sensitive personal
data and can enable discrimination.

## Decision
- **On by default:** nationality, current location, visa status, notice period or earliest
  joining date.
- **Off by default:** photo, date of birth and marital status, each with a
  **per-application toggle**. A field can be turned on only if the owner has supplied it.
  Nothing is inferred.
- Defaults come from the market pack (`cv_fields_default_on`, `cv_fields_default_off`,
  `photo_on_cv`). The toggle state is stored in the application's submitted payload.

## Consequences
- Positive: minimal personal data by default, in line with the DPDP Act and GDPR, and the
  owner stays in control.
- Negative: the `MarketPack` schema must be extended at Phase 2 start, and the toggles need
  UI in Telegram and the dashboard.
