# ADR-0007: YAML profile, PyYAML, facts-only resume parsing

- **Status:** Accepted
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "Profile parsing"
- **Related:** CLAUDE.md rule 1; PRD US-1.1, US-1.4

## Context
The profile is the source of every fact the system may use. It must be validated, readable
and editable by the owner. Resume parsing must never invent facts.

## Decision
- The profile, answer bank and packs are YAML. They are loaded with **PyYAML**
  (`safe_load`) and validated with Pydantic (`extra="forbid"`).
- The Phase 1 resume parser reads **UTF-8 plain text** and extracts **explicit labels
  only**.
- The later LLM-based PDF/DOCX parser produces a **draft** in which every field cites its
  source span. The draft becomes the profile only after the owner confirms it.

## Consequences
- Positive: no hidden inference, readable diffs, and strict validation.
- Negative: plain-text parsing is limited until the LLM gateway exists. `pypdf` and
  `python-docx` are added then.
