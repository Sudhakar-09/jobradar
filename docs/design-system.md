# JobRadar — Design system

| | |
|---|---|
| Status | Draft for owner review |
| Version | 0.1 (2026-10-30) |
| Brand direction | **A — Calm Compass**, with Direction B's celebration animation for interviews and offers only (owner choice, ADR-0025) |
| Preview | [`docs/design/brand-directions.html`](design/brand-directions.html) (Direction A column) |
| Related | `docs/ux.md` (screens), ADR-0014 (stack), ADR-0015 (tokens and quality gates), ADR-0020 (i18n, RTL, fonts), PRD §6 (E1–E10) |

This document is the source for `frontend/packages/tokens` and `frontend/packages/ui`. Values
here are the tokens; components may use **only** tokens (lint-enforced, `docs/coding-standards.md`
§13). A change to a token changes this file in the same PR.

---

## 1. Brand

### 1.1 Personality
**Calm Compass: a steady guide that makes a stressful search feel manageable.**

| We are | We are not |
|---|---|
| Calm, clear, reassuring | Hype, urgency, countdown pressure |
| Confident and honest about uncertainty ("we're not sure; here's why") | Falsely certain, or vague |
| Encouraging about progress (interviews, offers, learning) | Gamified for volume ("You applied to 50 jobs!") |
| Respectful of privacy and time | Noisy, nagging, attention-seeking |
| For everyone: any field, country, seniority | Tech-bro, insider jargon |

### 1.2 Logo concept
- **Mark:** a radar sweep inside a rounded square: two concentric rings, one sweep line, one
  "found" dot. It reads as both *radar* (discovery) and *compass* (direction).
- **Construction:** 40-unit grid, outer radius 10 (matches `--radius-lg` proportionally), ring
  stroke 2, sweep at 35° from the centre, dot radius 2.4. Final artwork is drawn by a designer;
  the preview mark is a placeholder.
- **Variants:** mark on `primary` (default), mark on `surface` (outline), monochrome, favicon
  (mark only, 16/32/48 px), app icon (maskable PWA icon with safe zone).
- **Wordmark:** "JobRadar" in Inter 650, tracking −0.02 em. In Arabic UI the Latin wordmark stays
  Latin.
- **Clear space:** the dot's diameter × 2 on every side. **Minimum size:** 16 px (mark), 80 px
  wide (lockup).

### 1.3 Voice and tone
Clear, warm, no jargon. Short sentences. Talk to the user ("you"), not about them.

| Situation | Tone | Do | Don't |
|---|---|---|---|
| Daily digest | Warm, brief | "Good morning. 6 new matches — 3 sponsor UAE visas." | "🚀 Crush your job hunt today!!" |
| Ineligible job | Honest, kind, useful | "This role needs an existing UAE residence visa. You told us you'd need sponsorship." | "You are not eligible." |
| Rejection email detected | Gentle, forward-looking | "Example Co decided not to continue. It's common at this stage — we'll keep looking." | "Rejected ❌" |
| Interview | Genuinely glad | "Interview with Demo Airlines on Tuesday. Your prep pack is ready." | "WOOHOO!!!" |
| Error | Calm, specific, actionable | "We couldn't reach Greenhouse. Your matches are safe; we'll retry in 10 minutes." | "Error 503: upstream failure" |
| Limit reached | Clear, no guilt | "You've reached today's 8 automated applications. Resets at midnight." | "Upgrade now!" |
| Unknown screening question | Respectful | "Example Co asks something we don't have an answer for. Answer once and we'll reuse it." | "Input required." |
| Privacy | Plain, specific | "We read only job-alert emails from the senders you chose. We never store the email text." | Legal-only wording |

Rules:
- Numbers and facts before adjectives. Never invent urgency.
- Never blame: "We couldn't…", not "You failed to…".
- Every system message is an i18n key with parameters (`docs/api.md` §3); copy is written in
  English first, translated by native speakers per market (PRD §8a.5).
- Celebrate outcomes (interview, offer), never activity counts.

## 2. Colour

### 2.1 Semantic tokens

All text/background pairs below were checked against WCAG 2.2 AA (≥ 4.5:1 for text) in both
themes; non-text UI (borders of inputs, focus rings, chart marks) meets ≥ 3:1. A unit test over
the token tables re-checks this in CI (ADR-0015).

| Token | Light | Dark | Use |
|---|---|---|---|
| `--color-bg` | `#F6F8F7` | `#0B1513` | Page background |
| `--color-surface` | `#FFFFFF` | `#111E1B` | Cards, panels, inputs |
| `--color-surface-2` | `#ECF2F0` | `#182824` | Subtle fills: chips, columns, pay boxes |
| `--color-line` | `#D3DFDB` | `#26403A` | Dividers and card borders (decorative) |
| `--color-line-strong` | `#7A8C87` | `#5B7A72` | Input borders, focusable outlines (≥ 3:1) |
| `--color-text` | `#132420` | `#E4EFEB` | Body text, headings |
| `--color-muted` | `#4B5E59` | `#9DB4AD` | Secondary text, labels |
| `--color-primary` | `#0F766E` | `#2DD4BF` | Primary actions, links, focus ring, brand |
| `--color-on-primary` | `#FFFFFF` | `#04302B` | Text/icons on primary |
| `--color-primary-soft` | `#D7EEEA` | `#133B35` | Selected rows, "why" callouts, highlights |
| `--color-accent` | `#A84B0C` | `#F4A65A` | Warm highlights: "this week", new, saved |
| `--color-success` | `#137336` | `#4ADE80` | Positive status, eligible, interview |
| `--color-warning` | `#A15C07` | `#FBBF24` | Soft concerns: notice period, stale FX rate |
| `--color-danger` | `#B91C1C` | `#F87171` | Destructive actions, errors, ineligible |
| `--color-info` | `#1D4ED8` | `#7AB0FF` | Neutral information, links in notices |
| `--color-overlay` | `rgb(19 36 32 / 0.45)` | `rgb(0 0 0 / 0.6)` | Dialog/sheet scrim |
| `--color-inverse-bg` / `--color-inverse-text` | `#132420` / `#F6F8F7` | `#E4EFEB` / `#0B1513` | Toasts, tooltips |

Status tints (badges, banners) are derived, not new colours:
`color-mix(in srgb, var(--color-<status>) 12%, var(--color-surface))` as background with the
status colour as text (all ≥ 4.5:1).

### 2.2 Measured contrast

Computed with the WCAG 2.x relative-luminance formula. Status colours are measured on
`surface-2`, the harder of the two surfaces they appear on.

| Pair | Light | Dark |
|---|---|---|
| text / bg | 15.13 | 15.78 |
| text / surface-2 | 14.24 | 13.05 |
| text / primary-soft | 13.30 | 10.47 |
| muted / surface | 6.90 | 7.81 |
| muted / surface-2 | 6.08 | 6.99 |
| on-primary / primary | 5.47 | 7.71 |
| primary / surface (links) | 5.47 | 9.21 |
| accent / surface-2 | 5.04 | 7.64 |
| success / surface-2 | 5.24 | 8.81 |
| warning / surface-2 | 4.57 | 9.20 |
| danger / surface-2 | 5.71 | 5.55 |
| info / surface-2 | 5.91 | 6.93 |
| inverse text / inverse bg (toasts) | 15.13 | 15.78 |
| line-strong / surface (non-text, ≥ 3:1) | 3.54 | 3.65 |

### 2.3 Rules
- **No colour outside the system.** Raw hex, rgb or named colours fail lint outside
  `packages/tokens`.
- Colour is never the only signal: status always has an icon and/or text (e.g. eligibility shows
  ✓/✕ icon + reason).
- Primary is for the **one** main action per view. Destructive actions use `danger` outline
  (filled only in the final confirm step).
- Dark theme is designed, not inverted: surfaces get lighter as they rise; shadows are
  replaced by subtle borders where shadows don't read.
- Theme: system preference by default; user override in Settings (`light` / `dark` / `system`),
  stored per user.

### 2.4 Data visualisation palette
Categorical series (in order; all ≥ 3:1 against `surface`):

| # | Light | Dark | Typical use |
|---|---|---|---|
| 1 | `#0F766E` | `#2DD4BF` | Main series (primary) |
| 2 | `#B4530F` | `#F4A65A` | Highlight / current period (accent) |
| 3 | `#2563EB` | `#7AB0FF` | Second category |
| 4 | `#7C3AED` | `#C4A5FF` | Third category |
| 5 | `#BE185D` | `#F58BB8` | Fourth category |
| 6 | `#4D7C0F` | `#A3D96A` | Fifth category |

- More than 6 categories → group the rest as "Other" (muted).
- Sequential scale (heat, intensity): 5 steps from `surface-2` to `primary`.
- Funnel stages use one hue (primary) with decreasing lightness, not a rainbow.
- Gridlines `line`; axis labels `muted` 12 px; values `text` 12 px tabular figures.

## 3. Typography

### 3.1 Families
| Role | Family | Notes |
|---|---|---|
| UI and display | **Inter** (variable, `wght` 400–700, `opsz` where available) | Self-hosted, subset per script, `font-display: swap`, metric-matched fallback (`Inter Fallback` from Arial with `size-adjust`) |
| Arabic script | **Noto Sans Arabic** (variable 400–700) | Loaded only for `ar`/RTL locales |
| Other scripts | Noto Sans `<script>` families added per locale (e.g. Devanagari) | ADR-0020 |
| Numbers | Inter with `font-variant-numeric: tabular-nums` for money, scores, counts | |
| Code (admin only) | System monospace | No extra font download |

### 3.2 Type scale (rem at 16 px root)

| Token | Size / line height | Weight | Tracking | Use |
|---|---|---|---|---|
| `--text-display` | 2.25 rem / 1.1 | 650 | −0.02 em | Landing hero, celebration headline |
| `--text-h1` | 1.875 rem / 1.15 | 650 | −0.02 em | Page titles ("Good morning") |
| `--text-h2` | 1.5 rem / 1.2 | 650 | −0.015 em | Section titles |
| `--text-h3` | 1.25 rem / 1.3 | 600 | −0.01 em | Card titles (job title) |
| `--text-h4` | 1.0625 rem / 1.35 | 600 | 0 | Sub-sections |
| `--text-body` | 1 rem / 1.5 | 400 | 0 | Default text |
| `--text-body-sm` | 0.875 rem / 1.45 | 400 | 0 | Secondary text, table cells |
| `--text-caption` | 0.8125 rem / 1.4 | 500 | 0 | Labels, meta |
| `--text-overline` | 0.75 rem / 1.3 | 600 | +0.08 em, uppercase (Latin only) | Eyebrows |

- Phones (< 640 px): `display` 1.875 rem, `h1` 1.5 rem; others unchanged.
- **Arabic adjustments:** line height +0.1, tracking always 0, no uppercase, weight 500 minimum for
  body (Arabic at 400 looks light on screens).
- Line length 60–75 characters for reading text (`max-width: 68ch`).

## 4. Layout: spacing, radius, elevation, grid

### 4.1 Spacing (4 px base)
`--space-0` 0 · `-1` 4 · `-2` 8 · `-3` 12 · `-4` 16 · `-5` 20 · `-6` 24 · `-8` 32 · `-10` 40 ·
`-12` 48 · `-16` 64 · `-20` 80 (px). Component padding uses 3/4/5; section gaps 6/8; page
margins 4 (phone) / 6 (tablet) / 8 (desktop).

### 4.2 Radius
| Token | Value | Use |
|---|---|---|
| `--radius-sm` | 8 px | Chips, badges, inputs, small buttons |
| `--radius-md` | 10 px | Buttons, cards inside panels, menus |
| `--radius-lg` | 14 px | Cards, panels, dialogs, sheets |
| `--radius-full` | 9999 px | Avatars, score ring, toggles |

### 4.3 Elevation
| Token | Light | Dark | Use |
|---|---|---|---|
| `--shadow-0` | none | none | Flat surfaces |
| `--shadow-1` | `0 1px 2px rgb(16 40 34 / .06), 0 1px 1px rgb(16 40 34 / .04)` | `0 1px 2px rgb(0 0 0 / .4)` + 1 px `line` border | Cards |
| `--shadow-2` | `0 8px 24px rgb(16 40 34 / .10)` | `0 10px 28px rgb(0 0 0 / .45)` | Hover lift, popovers, dragged card |
| `--shadow-3` | `0 16px 48px rgb(16 40 34 / .16)` | `0 18px 48px rgb(0 0 0 / .55)` | Dialogs, command palette |

### 4.4 Z-index
`--z-base` 0 · `--z-sticky` 10 · `--z-dropdown` 20 · `--z-overlay` 30 · `--z-dialog` 40 ·
`--z-toast` 50 · `--z-celebration` 60.

### 4.5 Breakpoints and grid
| Token | Min width | Columns | Gutter | Margin | Typical layout |
|---|---|---|---|---|---|
| `xs` | 360 px | 4 | 16 | 16 | Single column, bottom tab bar |
| `sm` | 640 px | 8 | 16 | 24 | Single column, wider cards |
| `md` | 768 px | 8 | 24 | 24 | List + detail as sheet |
| `lg` | 1024 px | 12 | 24 | 32 | Side nav + content |
| `xl` | 1280 px | 12 | 24 | 32 | Side nav + list + detail (3 panes) |
| `2xl` | 1536 px | 12 | 32 | auto | Content max width 1440 px, centred |

- Layout is designed from 360 px up (mobile first). No horizontal page scroll at any width.
- Touch targets ≥ 44 × 44 px on touch devices; ≥ 32 px on pointer devices with 8 px spacing.
- No layout shift: images and charts reserve space; skeletons match final sizes (CLS < 0.1).

## 5. Motion

### 5.1 Tokens
| Token | Value | Use |
|---|---|---|
| `--duration-fast` | 160 ms | Hover, press, small state changes |
| `--duration-base` | 220 ms | Most transitions, toasts, menus |
| `--duration-slow` | 320 ms | Page transitions, sheets, card moves, score reveal step |
| `--duration-celebrate` | 380 ms base, total ≤ 1.2 s | **Celebration only** |
| `--ease-standard` | `cubic-bezier(0.2, 0, 0, 1)` | Default (gentle ease-out) |
| `--ease-exit` | `cubic-bezier(0.4, 0, 1, 1)` | Elements leaving |
| `--ease-celebrate` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | **Celebration only** (spring with slight overshoot, from Direction B) |
| `--lift` | `translateY(-2px)` | Hover lift on cards/buttons |
| `--press-scale` | `0.98` | Button press |

### 5.2 Rules: when to animate
1. **Animate to explain change** (where something went, what changed), never to decorate.
2. Gentle everywhere: ease-out, no bounce, no overshoot — **except** the celebration.
3. Durations 150–300 ms for UI; nothing blocks input (animations are interruptible).
4. Animate `transform` and `opacity` only (no layout properties) to keep 60 fps.
5. Lists: stagger ≤ 30 ms per item, maximum 6 items; the rest appear together.
6. Loading content uses **skeletons** that match final layout; spinners only inside buttons for
   actions under way.
7. `prefers-reduced-motion: reduce` (or the in-app setting) → durations become ~0, no
   translate/scale, no celebration particles; state changes still happen instantly with the same
   end state.

### 5.3 Catalogue
| Moment | Motion |
|---|---|
| Page transition | Outgoing fades 120 ms; incoming fades + rises 8 px, `duration-slow`, `ease-standard` |
| Button press | Scale to `press-scale` on press, back on release, `duration-fast` |
| Card hover (pointer) | `lift` + `shadow-2`, `duration-fast` |
| Score reveal | Ring stroke draws to value and number counts up, 900 ms total, `ease-standard`; runs once per job per session |
| Pipeline card move (drag and drop or "Move") | FLIP: card follows pointer with `shadow-2` and 1.02 scale; on drop it settles into the target column in `duration-slow`; other cards shift with `duration-base` |
| Apply success | Button morphs to a check (icon cross-fade) + success toast slides up 16 px, `duration-base` |
| Toast | Enter: rise 16 px + fade; exit: fade 160 ms; auto-dismiss 5 s (paused on hover/focus) |
| Sheet / dialog | Sheet slides from inline-end (or bottom on phones) `duration-slow`; dialog scales 0.98→1 + fade; scrim fades |
| Swipe (mobile feed) | Card follows finger; past threshold it flies out with a tint (primary = apply, muted = skip) in `duration-base`; snap back otherwise |
| Skeleton | Shimmer 1.6 s linear loop, low contrast; disabled under reduced motion (static fill) |
| **Celebration (interview, offer only)** | From Direction B: 18 small confetti marks in primary/accent/success/info burst from the triggering card with `ease-celebrate`, fade out ≤ 1.2 s; the status badge pops with a 1.04 overshoot. Plays **once per event** (stored as seen), never for applications sent, never in digests or notifications, never during a page load. Reduced motion → static success banner only. |

## 6. Design tokens (implementation)

```
frontend/packages/tokens/
├── src/tokens.json        source of truth: primitives + semantic tokens + modes (light/dark)
├── src/build.ts           emits the files below; fails if any contrast check fails
├── dist/tokens.css        :root (light), [data-theme="dark"], @media (prefers-color-scheme: dark)
├── dist/tailwind-preset.ts Tailwind theme mapping every utility to CSS variables
└── dist/tokens.d.ts       typed token names for TS (e.g. motion presets)
```

- **Naming:** `--<category>-<name>[-<variant>]`: `--color-primary`, `--space-4`,
  `--radius-lg`, `--duration-base`, `--ease-standard`, `--text-h1-size`, `--shadow-2`.
- **Tailwind:** colours as `rgb(var(--color-x-rgb) / <alpha-value>)` so opacity utilities work;
  spacing, radius, shadow, z-index, font sizes and durations map to the same variables. Tailwind's
  default palette is **removed** so `bg-red-500` cannot be used.
- **Theme switching:** `data-theme` on `<html>`; `system` follows `prefers-color-scheme`. Theme
  is applied before first paint (inline script reads the stored preference) to avoid a flash.
- **Motion presets** for Motion (Framer Motion) live in `packages/ui/motion.ts` and read the same
  tokens: `fadeRise`, `sheet`, `toast`, `cardMove`, `celebrate`; each has a reduced-motion variant.
- **Lint:** ESLint + a Tailwind class check reject raw colours/sizes/durations and arbitrary
  values (`w-[13px]`) outside `packages/tokens` (ADR-0015).

## 7. Components (`packages/ui`, shadcn/ui on Radix)

Every component ships with Storybook stories for: light and dark, LTR and RTL, all variants,
and the states listed (default, hover, focus-visible, active/pressed, disabled, loading, error,
empty where relevant). Screens may only use these components.

| Component | Variants | States / notes |
|---|---|---|
| Button | primary, secondary, ghost, danger, link; sizes sm/md/lg; icon-only | loading (inline spinner, keeps width), disabled with reason tooltip |
| Input, Textarea | default, with prefix/suffix (currency) | error with message, helper text, character count; `line-strong` border |
| Select, Combobox | single, multi, searchable (roles, markets) | async loading, empty result |
| Checkbox, Radio, Switch | — | indeterminate (checkbox); Switch for instant settings only |
| Tabs, SegmentedControl | — | keyboard arrows, RTL order |
| Card | plain, interactive | hover lift (interactive only) |
| **JobCard** | compact (feed), expanded (today), swipeable (mobile) | eligible / ineligible (reason) / possible match; saved; new badge |
| **ScoreRing** | 32, 48, 64 px | animated reveal; text alternative "Fit 86 of 100"; "unscored" state with on-demand action |
| **EligibilityList** | — | ✓/✕/? icons + reason text from message keys |
| **PayComparison** | 1–3 columns | assumptions disclosure (FX rate + date, tax regime); "not disclosed"; stale-rate badge |
| **PipelineBoard**, Column, PipelineCard | — | drag and drop (pointer, touch, keyboard: Space to lift, arrows to move, Space to drop), invalid drop explained, optimistic move with rollback |
| Badge / Tag | neutral, primary, success, warning, danger, info, accent | always with text |
| Banner | info, warning, danger, paused, offline | dismissible where safe |
| Toast | success, info, warning, danger | action (Undo), auto-dismiss, `aria-live="polite"` |
| Dialog, AlertDialog, Sheet, Popover, Tooltip, DropdownMenu, ContextMenu | — | Radix focus management; Escape closes; return focus |
| CommandPalette | — | Ctrl/⌘+K; fuzzy search across actions, jobs, applications, settings |
| Stepper (onboarding) | horizontal (desktop), compact (phone) | completed, current, upcoming, error |
| Skeleton | text, card, chart, table row | matches final dimensions |
| EmptyState | — | illustration + one-line explanation + primary next action |
| DataTable (admin) | — | sort, filter, pagination (cursor), row actions |
| Chart wrappers (Recharts): FunnelChart, BarChart, LineChart, ComparisonBars | — | token palette, accessible table alternative ("View as table"), empty state |
| UsageMeter | — | value/limit with reset time; warning ≥ 80 % |
| Celebration | interview, offer | see §5.3; mounted once per event |
| Avatar, CompanyLogo | — | initials fallback; no external logo hotlinking |

## 8. Iconography
- **Lucide** icons only, 2 px stroke, sizes 16 / 20 / 24, `currentColor`.
- Icons accompany text for status and actions; icon-only buttons have an accessible label and a
  tooltip.
- **RTL mirroring:** directional icons (arrows, chevrons, "back", "forward", "send", progress) are
  mirrored; non-directional ones (check, clock, search, play) are not. The mirrored list lives in
  `packages/ui/icons.ts`.

## 9. Illustrations and empty states
- **Style:** simple geometric line illustrations, 2 px strokes in `muted`, one soft fill in
  `primary-soft`, one small accent dot in `accent` (echoing the logo's "found" dot). Friendly, not
  cartoonish; no people with specific ethnicity, gender or attire (works across cultures).
- **Format:** inline SVG components using tokens, so they follow light/dark and stay crisp.
- **Set (v1):** empty feed, empty pipeline, no interviews yet, no offers yet, all caught up,
  offline, error, paused, onboarding steps (5), connect inbox, extension.
- **Empty states guide to the next action:** one sentence of context + one primary button, e.g.
  "No matches yet — we check new jobs every 2 hours. **Broaden your markets**".

## 10. Accessibility (WCAG 2.2 AA)
- Contrast as §2 (checked in CI); focus ring 2 px `primary` + 2 px offset, always visible on
  keyboard focus (`:focus-visible`).
- Full keyboard operation including drag and drop and swipe alternatives (buttons).
- Landmarks, headings in order, labels for every control, `aria-live` for toasts and async
  results, `aria-describedby` for errors.
- Target size ≥ 24 × 24 px minimum (WCAG 2.5.8), 44 px on touch.
- Motion: §5.2 rule 7. No flashing content.
- Text resizes to 200 % without loss; layout reflows at 320 CSS px.
- Charts have a data-table alternative; colour is never the only encoding.

## 11. Internationalization and RTL
- `dir` set on `<html>` from locale; CSS logical properties only (`margin-inline-start`,
  `inset-inline-end`, `text-align: start`).
- Money, numbers, dates via `Intl` with the user's locale and time zone; currency codes shown where
  ambiguous (AED, INR). Latin digits by default in Arabic UI for money (common in the UAE),
  configurable per locale.
- Mixed-direction strings (Latin company names, skills, amounts in Arabic text) are isolated with
  `<bdi>` / `unicode-bidi: isolate`.
- Text expansion: layouts tolerate +40 % length (German, Arabic); no fixed-width buttons with text.

## 12. Process and quality gates
1. **Tokens first** (`packages/tokens`), with the contrast test.
2. **Components in Storybook** (`packages/ui`): every component, every state, light/dark, LTR/RTL.
   The owner reviews Storybook in the browser before screens are built (PRD E10).
3. **Screens only from components** (`apps/web`).
4. **CI:** Playwright visual regression over all stories and key screens (viewports 360, 768, 1280,
   1920; light/dark; LTR/RTL); axe checks; Lighthouse CI budgets ≥ 90 for performance,
   accessibility and best practices; token lint; i18n lint (no literals, no missing keys).
5. Visual baseline updates need a PR note explaining the change.
