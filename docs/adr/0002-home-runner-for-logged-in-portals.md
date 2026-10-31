# ADR-0002: Home runner for logged-in portals

- **Status:** Accepted; **amended by ADR-0016**. The browser extension is the default and the
  home runner is an optional, off-by-default mode. The rules below still apply to that mode.
- **Date:** 2026-10-30 (recorded; agreed earlier in chat)
- **Decision log:** 2026-10-30 — "Logged-in portal execution"
- **Related:** CLAUDE.md rule 5, PRD US-8.1, `docs/lld/runner.md`

## Context
Some useful portals need a logged-in session: Naukri, and possibly some Gulf portals where
their terms allow it. Keeping portal passwords or cookies on a cloud VM creates a high-value
secret. It also produces a location and device mismatch that portals flag as suspicious.

## Decision
Logged-in portal work runs **only** on a small **home runner** on the owner's machine, using
a persistent local Playwright browser profile. The runner **pulls** tasks from the API with a
scoped, revocable runner token. It runs them locally and reports results (status,
screenshot, submitted payload). **Cookies and credentials are never uploaded.**

## Consequences
- Positive: credentials never leave the home machine. The session uses a residential IP and
  a real browser profile, and the platform never connects into the home network.
- Negative: the lane works only while the home machine is on. A missing heartbeat marks the
  runner offline. Tasks then stay queued with a TTL and are never moved to the cloud.
- Negative: there are two deployables to version. The runner protocol is versioned under
  `/api/v1/runner`.

## Alternatives considered
- **Credentials in a cloud vault:** violates CLAUDE.md rule 5.
- **Browser extension:** a more complex distribution and permission model. Can be revisited
  after Phase 9.
