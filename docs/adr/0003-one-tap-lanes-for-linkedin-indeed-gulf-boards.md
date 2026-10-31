# ADR-0003: One-tap lanes for LinkedIn, Indeed and Gulf boards

- **Status:** Accepted
- **Date:** 2026-10-30 (LinkedIn/Indeed agreed earlier; Gulf boards added at PRD review)
- **Decision log:** 2026-10-30 — "LinkedIn and Indeed applications"; "PRD review: Naukrigulf"
- **Related:** CLAUDE.md rule 4, PRD US-5.5, ADR-0008

## Context
LinkedIn Easy Apply and Indeed Apply forbid automated use. Automating them risks account bans
and harm to the owner's reputation. Bayt, Naukrigulf and GulfTalent have no public APIs, and
scraping them would break the "respect sources" rule (CLAUDE.md rule 7).

## Decision
These platforms are **one-tap lanes**. The system prepares everything (the selected and
tailored CV, a cover note, answers to likely screening questions, and the link) and sends it
to the owner, who applies manually. The owner then taps an "I applied" button, which records
the transition with trigger `user`. **No submit code, form-filling or scraping is written for
these platforms.** Jobs from them are discovered only through job-alert emails (ADR-0008).

## Consequences
- Positive: no terms violations, and the owner stays in control on the most visible
  platforms.
- Negative: each application costs the owner time. Good preparation and strategy-driven
  volume reduce this.
- Enforcement: the apply adapter registry refuses lane `auto` or `careful` for hosts on a
  `one_tap_only` list. A unit test asserts this.

## Alternatives considered
- **Automating with human-like behaviour:** violates platform terms. Rejected.
