# ADR-0022: Source policy registry governs automation per host

- **Status:** Accepted
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "Source policies"
- **Extends:** ADR-0003 (one-tap lanes), CLAUDE.md rules 4 and 7
- **Related:** PRD v0.3 §4.4, US-2.8, US-8.3; ADR-0016

## Context
With many sources across many countries, rules like "LinkedIn is one-tap only" can't stay
scattered through the code. Connectors, server-side apply adapters and the browser extension all
need the same answer to "what are we allowed to do on this host?"

## Decision
- `config/source_policies.yaml` lists every host or source with: allowed **access modes**
  (`api`, `ats_feed`, `alert_email`, `extension_assist`, `server_apply`, `one_tap`, `none`),
  rate limits, User-Agent, terms URL, notes and `last_reviewed`.
- The policy is validated on load. **Default for an unknown host: `one_tap` only.**
- Connectors, apply adapters and the extension's host-permission list read the policy. A CI test
  fails if any connector or adapter targets a host without a policy entry, or with a mode the
  policy doesn't allow.
- Initial entries: LinkedIn, Indeed, Bayt, Naukrigulf and GulfTalent → `alert_email` +
  `one_tap`; public ATS boards → `ats_feed` (+ `extension_assist`, and `server_apply` per ATS
  after a terms review); Naukri → set after a terms review in Phase 8.
- Policy changes are reviewed like code and recorded in the decisions log.

## Consequences
- Positive: one place to check compliance, and safe defaults for new hosts.
- Negative: someone must review each source's terms before enabling any mode beyond `one_tap`.
