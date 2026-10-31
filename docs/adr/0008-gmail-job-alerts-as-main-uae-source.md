# ADR-0008: Gmail job-alert ingestion as main UAE source (Phase 2)

- **Status:** Accepted
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "PRD review: Gmail ingestion moves into Phase 2"
- **Related:** PRD US-2.5, US-2.7, US-6.2, R1/R1a/R1b; ADR-0003

## Context
UAE coverage is the biggest product risk (PRD R1):
- Adzuna does not cover the UAE.
- Gulf boards have no public APIs.
- Many UAE employers use ATSs without public job feeds.

The owner can subscribe to job alerts on LinkedIn, Naukrigulf, Bayt and GulfTalent, and
those alerts arrive in Gmail.

## Decision
- Move **read-only Gmail ingestion of job-alert emails** into **Phase 2** as a discovery
  connector (`gmail_alerts`). It uses the `gmail.readonly` scope, and its query is limited to
  configured alert senders and labels.
- Write one `AlertEmailParser` per sender format, tested against anonymized `.eml` fixtures.
- Store only the parsed job fields and the Gmail message ID. Discard the raw body after
  parsing. A message that fails to parse keeps only its ID, so it can be replayed later.
- Put the Gmail client in `core/gmail` so `lifecycle` can reuse it in Phase 6.
- **Inbox-based application tracking stays in Phase 6.** Widening the query beyond alert
  senders needs the owner's explicit consent, recorded in `audit_log`.
- Add a **curated list of UAE-hiring companies** on Greenhouse, Lever, Ashby, Workable and
  SmartRecruiters, seeded from employers seen in alerts (US-2.7).

## Consequences
- Positive: real UAE coverage from Phase 2 without scraping, and dedupe across alerts and
  ATS feeds.
- Negative: OAuth setup moves earlier. Alert volume depends on which alerts the owner sets
  up, which a setup guide will cover. Email formats change; `degraded` detection on each
  parser catches this.
- Privacy: a narrow query, discarded bodies and an encrypted token limit exposure.
