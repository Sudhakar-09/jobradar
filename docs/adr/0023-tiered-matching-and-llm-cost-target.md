# ADR-0023: Tiered matching pipeline and LLM cost target

- **Status:** Accepted (pgvector approved 2026-10-30)
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "Tiered matching and cost target"
- **Related:** PRD v0.4 US-3.7, §9; `docs/architecture.md` §8a, §13; ADR-0019

## Context
HLD v0.2 estimated about 3.9 M LLM tokens per user per month, from LLM-scoring every job that
passed the rule filters (about 40 per day) with the full posting. That is too high for
Stage 3. Matching quality must not fall when costs come down.

## Decision
- **Tier 0: rules and hard filters** (no LLM): market/role flags, location and remote region,
  visa, licence, language, experience, excluded keywords, already-seen jobs.
- **Tier 1: embedding similarity.** Each job is embedded **once** (shared, keyed by content
  hash). Each profile is embedded once per profile version. Take the top K (default 50) by
  cosine similarity.
- **Tier 2: LLM fit scoring** only for each user's **top N** (`matching.llm_top_n`, default 10,
  plan-limited). Requests are batched (default 5 jobs per call with one shared profile block)
  and use compact structured job summaries.
- **Model tiers by task:** `small` for normalization and classification, `standard` for fit
  scoring, `premium` only for tailoring when the plan allows. Model names are config.
- **Caching:** normalization by job content hash; scores by (job hash, profile version, prompt
  version); identical prompts served from the response cache. Optional provider batch APIs for
  overnight re-scoring.
- **Fallback for jobs below the cut:** shown as "possible match" with a similarity-based reason,
  and the user can score one on demand (counted against their budget).
- **Target:** ≤ 0.8 M generative tokens and ≤ US$0.20 LLM cost per MAU per month at Stage 3.
  The estimate after tiering is about 0.68 M tokens and US$0.15, down from about 3.9 M and
  US$0.80 (`docs/architecture.md` §13.2; prices are illustrative and must be re-checked).
- **Quality guard:** the Tier 2 coverage metric (share of applied jobs that were in the top N)
  must stay ≥ 90%. Thumbs feedback feeds the eval set.
- **Vector storage:** pgvector in the existing Postgres (shared `job_embeddings`, user-owned
  `profile_embeddings` under RLS; HNSW index when the corpus grows). The owner **approved** it
  on 2026-10-30: compose uses the official `pgvector/pgvector:0.8.0-pg16` image, and the
  `pgvector` Python package is added in Phase 3.

## Consequences
- Positive: about 80% lower LLM cost per user. Shared work (normalization, job embeddings)
  amortizes as users grow.
- Negative: more moving parts (embedding model choice, index tuning). Some good jobs may fall
  below the cut, which the coverage metric and on-demand scoring mitigate.

## Alternatives considered
- **LLM-score everything that passes rules:** simplest and too expensive.
- **Embeddings only, no LLM:** cheapest, but no explanations or matched/missing skills, which the
  PRD requires (G3).
- **External vector database:** unnecessary at this scale. pgvector keeps a single datastore.
