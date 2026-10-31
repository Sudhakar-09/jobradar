# ADR-0011: Celery with per-domain queues and idempotent tasks

- **Status:** Accepted (Step 2 review, 2026-10-30). HLD v0.2 adds a `notify` queue with an
  outbox and per-user fairness.
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "Step 2 review"
- **Related:** PRODUCT_STANDARDS J, G; `docs/architecture.md` §4; ADR-0001

## Context
The workloads differ sharply:
- discovery: polite I/O
- LLM calls: rate-limited
- apply: a single browser with human pacing
- inbox sync: per user

A failure or backlog in one must not starve the others, and nothing may ever be submitted
twice.

## Decision
- Use Celery + Redis with queues `discovery`, `llm`, `apply`, `email`, `notify` and `default`. Each
  queue has its own worker process and concurrency; apply has concurrency 1.
- Set `acks_late` and `reject_on_worker_lost`. Every task is **idempotent**, keyed on a
  natural key, and task arguments are IDs only.
- Retry with exponential backoff and jitter, for transient errors only. **Apply tasks never
  retry automatically after the submit click.** An uncertain outcome goes to
  `needs_review`.
- When retries run out, write a `dead_letters` row that can be replayed from the admin
  console.
- Use per-user Redis locks for apply and inbox. Carry the correlation ID in task headers.

## Consequences
- Positive: workloads are isolated, throughput is predictable, and redelivery is safe.
- Negative: more processes on a small VM. Low concurrency and memory limits keep this in
  check.

## Alternatives considered
- **RQ or Dramatiq:** simpler, but weaker scheduling and routing, and the stack is already
  fixed.
- **Single queue:** simplest, but one slow Playwright task would block discovery.
