<!-- PR title must follow Conventional Commits, e.g. "feat(matching): tiered pipeline" (CI checks it). -->

## What and why

<!-- One or two sentences. Link the PRD story/stories this implements. -->

- PRD stories: US-
- LLD sections checked: `docs/lld/<module>.md` §
- ADRs / decisions affected:

## Contract and schema changes

- [ ] No API contract change, **or** `docs/openapi.yaml` + `docs/api.md` updated and the reason is stated here:
- [ ] No schema change, **or** migration follows `docs/lld/database.md` §7 (expand → migrate → contract, working downgrade, RLS in the same migration) and `database.md` is updated in this PR
- [ ] No new dependency, **or** the owner approved it (link) and it is recorded in `docs/decisions-log.md`

## Self-review (docs/coding-standards.md and docs/PRODUCT_STANDARDS.md)

- [ ] Follows the flow: PRD story → LLD checked → code → tests → self-review
- [ ] Layering respected (entry points → services → repositories → models; `lint-imports` passes)
- [ ] Typed (mypy strict), Google docstrings on public modules, classes and functions
- [ ] Errors use the `JobRadarError` hierarchy; no bare or blind `except`
- [ ] Every I/O call has a timeout; no blocking calls in async code
- [ ] No magic numbers, hardcoded URLs or secrets; config via settings, packs or flags
- [ ] Logs use `<module>.<event>` names and contain no personal data
- [ ] Tenancy: every user-owned query takes `UserScope`; isolation test added for new endpoints/tables
- [ ] Never-fabricate, dry-run-by-default, caps/kill switch and source-policy rules still hold (`CLAUDE.md` §2)
- [ ] Untrusted text (job posts, emails, page content) is never interpolated into prompt instructions or logged
- [ ] UI changes: built from design-system components, tokens only, i18n keys, LTR + RTL, light + dark, states (loading/empty/error/offline) covered

## Tests

- [ ] Unit tests for new logic; fixtures/golden data for connectors and parsers (no live calls)
- [ ] Conformance / synthetic users still green where packs, normalizer or matching changed
- [ ] `uv run pre-commit run --all-files` passes locally

## Project memory

- [ ] `docs/progress.md` updated (and `docs/decisions-log.md` if a decision was made)
- [ ] README / CHANGELOG updated if this completes a phase
