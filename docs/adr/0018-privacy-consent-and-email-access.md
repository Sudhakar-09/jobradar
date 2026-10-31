# ADR-0018: Privacy, per-source consent and email access strategy

- **Status:** Accepted
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "Trust and legal"
- **Related:** PRD v0.3 §7.3, US-2.5, US-6.2, US-10.3, US-10.7, US-11.2; ADR-0008; PRODUCT_STANDARDS P, X

## Context
JobRadar processes CVs, emails and personal details for many users across India (DPDP Act
2023), the EU (GDPR) and other jurisdictions. Gmail `readonly` is a restricted Google scope.
Google limits unverified apps to a small number of test users and requires verification and a
periodic security assessment for public apps that use it.

## Decision
- **Consent per data source** (alert inbox, inbox tracking, extension, Telegram, each portal
  integration). Each consent is stored with purpose, scope, consent-text version and timestamp.
  Revoking it takes effect immediately: tokens are revoked and ingestion stops.
- **Rights:** access, correction, export (JSON + CSV + documents) and full deletion (hard delete
  of user content within a stated period; backups age out by retention policy). A grievance
  contact is provided.
- **Minimisation:** sensitive fields are optional and off by default, and never inferred. Alert
  email bodies are discarded after parsing. Logs contain no PII.
- **Legal documents:** privacy policy and terms published before Stage 2. Consent texts are
  versioned, and material changes require re-consent.
- **Email access strategy:**
  - Stage 1–2: Gmail API (`readonly`) with a narrow query, within Google's test-user limit.
  - Stage 3 default: a **per-user forwarding address**. The user forwards alert emails to
    their private JobRadar inbound address, so no Google restricted scope is needed. Gmail API
    stays available only if Google verification is completed.
  - Both sit behind the `AlertInbox` interface, so parsers don't change.

## Consequences
- Positive: legally defensible consent trail, and the public launch doesn't depend on Google
  verification.
- Negative: forwarding needs user setup (guided in onboarding) and an inbound mail provider
  (chosen in Phase 11). It must also show the user the forwarding-confirmation message from
  their mail provider.
