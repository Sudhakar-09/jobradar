# ADR-0021: Role taxonomy, field documents and credentials

- **Status:** Accepted (backbone licensing check open)
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "Role taxonomy across all fields"
- **Related:** PRD v0.3 §4.2, US-1.2 AC3, US-3.1, US-3.2; ADR-0006, ADR-0013

## Context
Supporting any role means placing any job title into a structure. Fields differ in signal
documents (portfolio, GitHub, publications), required credentials (licences, registrations,
certifications, often per country) and hiring patterns (referral vs volume, seasonality,
assessment types).

## Decision
- **Three levels: field → role family → role.** Each level is backed by a public occupational
  classification so unknown titles can still be placed:
  - **ISCO-08** (ILO) major and minor groups as the stable backbone.
  - **ESCO** occupations and skills where its reuse terms allow, checked before Phase 3. If
    the terms don't allow it, ISCO-08 groups are used alone.
- **Role packs** add the job-search knowledge: title aliases (multi-language), core skills,
  adjacent roles, signal documents, `required_credentials` and `valued_credentials` **per
  market**, hiring patterns (stages, assessment types, seasonality, time-to-hire) and resume
  emphasis.
- **Eligibility uses credentials:** a role pack that requires a licence in a market produces a
  plain-language eligibility reason when the profile lacks it ("Requires a DHA nursing licence
  for Dubai; add it in your profile if you have one"). The system never assumes a credential.
- The initial pack authoring order is listed in PRD §4.2. Each pack passes the golden pipeline
  test.

## Consequences
- Positive: any title maps somewhere, and field-specific advice is data, not code.
- Negative: credential facts go stale, so each pack carries `last_verified` and official
  links, like market packs.
