# ADR-0014: Web app stack; Streamlit removed

- **Status:** Accepted
- **Date:** 2026-10-30
- **Decision log:** 2026-10-30 — "Web app is the main product; premium UI stack"
- **Supersedes:** the "Dashboard (v1): Streamlit" row of `CLAUDE.md` §3 (updated in Step 7)
- **Related:** PRD v0.3 §5, §6; ADR-0015, ADR-0020; `docs/architecture.md` §3

## Context
The web app is now the main product for many users. It must feel premium, at the level of
Linear, Stripe or Notion, with motion, drag and drop, a command palette, offline support, i18n
and RTL. Streamlit can't deliver that level of interaction design or performance.

## Decision
- **Frontend stack:** React + TypeScript (Vite), Tailwind CSS, shadcn/ui on Radix primitives,
  Motion (Framer Motion) for animation, TanStack Query for server state, Lucide icons,
  **Recharts** for charts (SVG, themed from tokens), Storybook, Vitest, Playwright (visual
  regression and end-to-end), Lighthouse CI.
- **Delivery:** an installable, mobile-first **PWA**. The static build is served by Caddy
  (and a CDN in Stage 3) on the same origin as `/api`.
- **Monorepo layout:** `frontend/` pnpm workspace with `packages/{tokens,ui,api-client,i18n}`
  and `apps/{web,extension}`. The TypeScript API client is generated from `docs/openapi.yaml`.
- **Streamlit is removed everywhere** (docs, compose, CLAUDE.md).
- Node LTS and pnpm become dev tools, and the frontend dependencies above are approved by the
  owner (2026-10-30). Any other frontend dependency needs approval (CLAUDE.md §11).

## Consequences
- Positive: full control of UX quality and performance, and one component system shared by the
  web app and the extension.
- Negative: a second language and toolchain, with more CI time (visual regression, Lighthouse).
- Follow-up: `docs/design-system.md` and `docs/ux.md` in Step 6; frontend CI jobs in Step 5.

## Alternatives considered
- **Next.js:** SSR is unnecessary for a logged-in app, and the landing page can be prerendered
  by Vite. It would add a server runtime.
- **Svelte/SvelteKit:** an excellent DX, but a smaller ecosystem for shadcn/Radix-quality
  accessible primitives.
- **Keep Streamlit for admin:** two UI stacks; rejected for consistency.
