# Phase 3 design check (2026-11-01)

CLAUDE.md §11 step 2 for Phase 3 (normalize and match): PRD stories US-3.1 … US-3.8 checked
against the LLDs (normalizer, matching, profile, quotas, database §9, README traceability),
`docs/openapi.yaml`, ADR-0009 / ADR-0023 and the Phase 2 decisions of 2026-10-31 / 2026-11-01.
Key findings were spot-checked against the files. No code was written.

## Story coverage

| Story | Design | Verdict |
|---|---|---|
| US-3.1 Normalization | normalizer.md §2–3 | gap (3, 4, 5, 6) |
| US-3.2 Eligibility with reasons | matching.md §3.2 | gap (1, 3, 4, 7) |
| US-3.3 AI fit score | matching.md §3.4, §9 | ready, depends on 8 |
| US-3.4 Ranking, `jobradar matches --top 20` | matching.md §3.5 | gap (12) |
| US-3.5 Pay comparison | normalizer.md compensation models (India, UAE only) | conflict (2, 9) |
| US-3.6 LLM metering and soft budget | lld/README core.llm, quotas.md | conflict (10) |
| US-3.7 Tiered matching and cost | matching.md §3.1–3.4, ADR-0023 | gap (8, 12) |
| US-3.8 Synthetic users | PRD §8a.2, matching.md §9 | conflict (11) |

## Gaps and conflicts (most important first)

1. **Market gate blocks the owner's own markets.** Rule `market_enabled` (matching.md §3.2)
   blocks jobs when `market.<code>.enabled` is off, and the flag needs passing conformance;
   only the UAE passes (India and Germany wait for alert readers).
2. **No Germany compensation model design.** `CompProfile` has only `india_tax_regime`; church
   tax is special-category data and must not be inferred; plug-in codes disagree (`"india"`,
   `"uae"` in normalizer.md vs `india_ctc`, `uae_package`, `germany_gross` in packs); tax data
   has two homes (`config/compensation/` in CLAUDE.md §5 and normalizer.md vs
   `config/market_data/` via `core.dated_data`); `DatedEntry.values` is a flat float map and
   cannot hold tax slabs or the § 32a EStG formula.
3. **`NormalizedJob` and the jobs columns cannot feed the Phase 2 rules:** missing title,
   description, company id / industries, posting language, minimum years and skills.
4. **Two seniority vocabularies:** role packs use junior / mid / senior / staff / executive;
   database.md `profiles.seniority` / `jobs.seniority` CHECK uses ten values without `staff`.
5. **normalizer.md predates Phase 2:** no `language_signals`, `seniority_signals`,
   `level_for_years`, minimum-years extraction or `conditional_title_aliases`.
6. **Skill extraction not designed** (matching needs required / preferred skills).
7. **`allowed_regions` has no vocabulary** (EU, EEA, EMEA → countries); needed by
   `remote_region` and syn-06.
8. **LLM and embeddings not concrete:** no provider, model IDs, prices or vector dimension; no
   `LLM_*` settings; recordings designed with `make` (repo uses `tasks.ps1`); LiteLLM makes its
   own HTTP calls, against "httpx via `core.http` only" (needs a recorded exemption or a custom
   transport); token counting; `core.plugins` registry designed but not built.
9. **FX keys inconsistent and no rates file** (ADR-0009 vs normalizer.md; no EUR pairs).
10. **`GET /me/usage` tagged Phase 3 but needs sign-in (Phase 4);** daily cost-per-user report
    needs a Phase 3 path (`metrics_daily` is Phase 9).
11. **US-3.8 AC1 (syn-01 … syn-10) cannot pass in Phase 3:** only India, UAE, Germany,
    `java_backend` and `mid` packs exist; syn-06 is underspecified.
12. **Phase 3 CLI unspecified** (`matches --top 20` output, possible matches, on-demand score,
    normalize / embed / match runs, usage report); no Celery tasks yet.
13. **Profile import mappings incomplete** (locations, skills, languages; `excluded_keywords`,
    `india_tax_regime`, `min_fit_score` not in the YAML schema).
14. Smaller: Stage 1 file storage for resume uploads; `pgvector` Python package approved in
    ADR-0023 but not listed in CLAUDE.md §4; 0003 indexes.

## Owner decisions needed

See the decisions requested on 2026-11-01 (market gate, LLM and embedding provider, dependency
pins, LLM budget, Germany net-pay defaults, synthetic-user scope, FX seed rates); outcomes go
to `docs/decisions-log.md`.

## Proposed sub-steps

3a doc fixes and decisions · 3b `core.plugins`, `core.llm` gateway, metering, migration 0003
part 1 · 3c migration 0003 part 2 (jobs normalized columns, profiles, embeddings, scores, RLS)
and profile import · 3d rules-first normalizer · 3e LLM field resolver · 3f FX and
compensation models (India, UAE, Germany) · 3g Tier 0 eligibility · 3h embeddings and Tier 1 ·
3i Tier 2 scoring, ranking, possible matches · 3j CLI · 3k synthetic users syn-01 / syn-06 ·
3l Phase 3 acceptance check.
