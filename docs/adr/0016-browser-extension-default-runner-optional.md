# ADR-0016: Browser extension by default; home runner optional

- **Status:** Accepted
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "Browser extension for logged-in portals"
- **Amends:** ADR-0002 (the home runner becomes an optional mode, not the default)
- **Related:** PRD v0.3 §5, US-8.1 … US-8.3; ADR-0003, ADR-0017, ADR-0022

## Context
A home runner suits one technical user, but most users won't install and run a background
service. Logged-in portals still must never expose credentials to the cloud, and the user must
stay in control.

## Decision
- A **Manifest V3 browser extension** (Chromium first, Firefox next) is the default way to work
  with logged-in portals. It runs in the user's own browser with the user's own session.
- **User in control:** the extension shows match and eligibility, assists form filling from
  the profile and answer bank, and highlights unknown questions. **The user reviews and clicks
  submit.** After submission it records proof (visible-tab screenshot and payload snapshot).
- **Permissions:** host permissions are requested at runtime, **only** for hosts whose source
  policy allows `extension_assist` (ADR-0022).
- **One-tap-only hosts (LinkedIn, Indeed, Gulf boards)** (refined at the v0.3 review): the
  extension **never reads, fills or clicks anything on the page**. It has no host permission and
  no content script there. It may open the browser's **side panel**, which is extension UI
  outside the page. The panel shows the prepared one-tap pack for a job the user picks from their
  JobRadar queue (answers, cover note, CV download), each with a **copy button**, and the user
  pastes everything themselves. "Save this job" reads only the tab URL and title, on an explicit
  click (`activeTab`). A build-time test checks the manifest against the source policy registry.
- **Auth:** paired from the web app with a short-lived code exchanged for a scoped, rotating,
  revocable extension token (ADR-0017). Cookies and credentials never leave the browser.
- **Safety:** page content is untrusted. The extension never runs page-provided instructions,
  and every assist goes through the same server-side guards (caps, quality threshold, pause).
- The **home runner** stays an **optional, off-by-default** mode for power users who want
  unattended logged-in tasks (ADR-0002 rules still apply).

## Consequences
- Positive: no install friction beyond the browser store, no credentials in the cloud, and a
  clear user-in-control story for store review and the law.
- Negative: browser store review cycles, and version skew with the API (handled by
  `X-Client-Version` and N-1 support).
- Follow-up: privacy disclosure for the store listing; extension threat model section.

## Alternatives considered
- **Home runner as default:** too much setup for non-technical users.
- **Cloud browser with uploaded cookies:** violates CLAUDE.md rule 5.
