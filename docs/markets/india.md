---
market: india
flag: market.india.enabled
checklist:  # PRD §8a.5; each item: done | open, with date and note
  pack_verified: {status: done, date: 2026-10-31, note: "packs/verification/india.yaml"}
  sources_connected: {status: open, note: "Indeed alert parser and India company catalogue pending"}
  conformance_green: {status: open, note: "jobradar packs check"}
  synthetic_users: {status: open, note: "Phase 3 (syn-01)"}
  golden_dataset: {status: done, date: 2026-10-31, note: "tests/golden/india (Indeed sample pending)"}
  translations_reviewed: {status: open, note: "Phase 4 (en-IN only)"}
  ui_matrix: {status: open, note: "Phase 4"}
  owner_sign_off: {status: open}
signed_off_by: null
---

# India rollout checklist

Required before `market.india.enabled` is turned on for users (PRD §8a.5). The admin rollout
gate reads this file's front matter from Phase 4 (docs/lld/admin.md); until then conformance
(`jobradar packs check`) is the enforced gate.

## Known gaps (owner decisions, 2026-10-31)

Stage 1 serves Indian citizens only. Before India is enabled for **non-Indian users**:

- **Employment Visa rules** for foreign nationals (Ministry of Home Affairs / Bureau of
  Immigration) must be added to the pack's `visa_routes` and verified against official sources.
- **Foreign degree equivalence** (e.g. Association of Indian Universities) must be added to
  `credential_recognition` and verified.

Also open: professional tax per state, to be added from state government sources (the pack keeps
only the verified "varies by state, at most ₹2,500 a year").
