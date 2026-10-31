# JobRadar — UX: journeys and screens

| | |
|---|---|
| Status | Draft for owner review |
| Version | 0.1 (2026-10-30) |
| Visual language | `docs/design-system.md` (Direction A — Calm Compass; celebration from Direction B) |
| Related | PRD v0.4 §5–§7 and stories, `docs/api.md` (endpoints), `docs/lld/*` (behaviour) |

Wireframes are schematic (layout and hierarchy, not pixels). Names, companies, salaries and the
example AED→INR rate in them are fictional illustrations, not data. Every screen is built only from
`packages/ui` components and tokens. Story IDs and endpoints link each screen to the PRD and API.

---

## 1. UX principles

1. **One clear next step.** Every screen has one primary action; everything else is secondary.
2. **Explain, don't just score.** Every number (fit, eligibility, pay) has a plain-language "why"
   one tap away.
3. **Calm by default.** No red unless something is actually wrong; no urgency we didn't verify; no
   activity-count gamification. Celebrate interviews and offers only.
4. **Fast and forgiving.** Optimistic updates, undo for destructive actions, nothing lost on
   reload or offline.
5. **The user is in control.** Automation is visible, paused with one tap, and never submits
   without the rules the user set (dry-run review, caps, quality threshold).
6. **Private by design.** Show exactly what we read, store and why, next to the control.
7. **Everyone, everywhere.** Works at 360 px, in RTL, with keyboard and screen reader, in any
   supported language and currency.

## 2. Information architecture

```
Web app (signed in)
├── Today                 (home: digest, questions, next steps)
├── Jobs                  (feed: matches + possible matches + saved)
│   └── Job detail        (sheet on list, full page on phone/deep link)
├── Pipeline              (board by state)
│   └── Application detail (timeline, documents, emails, proof)
├── Interviews            (upcoming, prep packs)
├── Offers                (list + comparison)
├── Insights              (funnel, callback rates, weekly report)
├── Settings              (profile, documents, answers, markets/roles, lanes & caps,
│                          notifications, connections, privacy, appearance, plan & usage)
└── Admin (admin/owner)   (system, connectors, queues, flags, rollout, users, abuse, LLM, audit)
Public: Landing · Sign in / Sign up · Legal (privacy, terms)
Extension: Popup · Side panel · In-page assist (allowed ATS hosts only)
Channels: Email digest · Web push · Telegram
```

**Navigation**
- **Desktop (≥ 1024 px):** left sidebar (logo, 7 primary items, Admin for admins, user menu at the
  bottom), collapsible to icons. Top bar per page: title, page actions, search trigger
  ("Search or jump… Ctrl K"), pause indicator.
- **Phone (< 768 px):** bottom tab bar with 5 items: Today, Jobs, Pipeline, Insights, More
  (Interviews, Offers, Settings, Admin). Top bar: title + search + pause indicator.
- **Global pause indicator:** when apply activity is paused, a `warning` pill "Paused" appears in
  every top bar; tapping it opens the pause control.

## 3. Global patterns

| Pattern | Behaviour |
|---|---|
| **Command palette** (Ctrl/⌘+K) | Fuzzy search across: actions ("Pause all applying", "Add answer", "Switch to dark mode"), jobs, applications, companies, settings pages. Recent items first. Opens in `duration-base` with `shadow-3`. |
| **Keyboard shortcuts** (`?` shows the list) | `g t` Today · `g j` Jobs · `g p` Pipeline · `g i` Insights · `j/k` next/previous item · `a` apply · `s` save · `x` skip · `o`/Enter open · `e` edit field · `z` undo · `/` focus search · `Esc` close. Single-key shortcuts are off while typing and can be disabled in Settings (WCAG 2.1.4). |
| **Optimistic updates** | Apply/Skip/Save/move update the UI immediately; on error the change rolls back with an explanatory toast (`docs/api.md` §6). |
| **Undo** | Skip, withdraw, delete answer, disconnect: toast with **Undo** for 10 s (server undo token). Irreversible actions (delete account) use a typed confirmation instead. |
| **Inline editing** | Profile fields, answers, contact notes: click/Enter to edit, Enter/blur saves (ETag), Esc cancels; validation inline. |
| **Instant search and filters** | Filters update results as you type (debounced 150 ms), reflected in the URL so views can be bookmarked and shared. |
| **Tooltips** | On icons, truncated text, and every score component ("Freshness: posted 2 days ago"). Never the only place for essential information. |
| **States** | Every data view defines: loading (skeleton), empty (illustration + next action), error (what happened + retry), success (toast or inline), offline (banner + cached read-only data + queued actions), partial (e.g. "Scoring delayed" badge). |
| **Offline** | App shell and last-viewed Today/Jobs cached. Banner: "You're offline. Showing what you saw last; actions will sync." Queued actions show a small clock icon until synced. |
| **Notifications** | In-app bell with unread count; items deep-link to the relevant screen. |
| **Celebration** | Interview or offer transition only (design-system §5.3), once per event. |

## 4. User journeys

### J1 — First run (any persona; user #1 = mid-level Java engineer, India + UAE)
```
Landing → Sign up (invite in Stage 2) → Verify email → Onboarding wizard:
 1 Resume upload → 2 Review draft (facts with source highlights) → 3 Markets & roles
 (+ credentials per market) → 4 Channels & consents (email digest, push, Telegram, alert inbox)
 → 5 Lanes & caps (dry-run on) → First matches preview → Today
```
Success: ≥ 5 eligible matches within 24 h (PRD activation metric). If fewer, the preview explains
why and offers one fix (e.g. "Add Remote as a market" or "Connect job alerts").

### J2 — Daily routine (5–15 min, often on the phone)
Digest (email/push/Telegram) at 08:00 local → tap → **Today** → answer 1 open question → swipe
through top matches (Apply/Skip/Save) → check one-tap pack for a LinkedIn job → done.

### J3 — Apply, by lane
- **One-tap (LinkedIn, Indeed, Gulf boards):** Apply → one-tap pack (CV, answers, cover note) →
  "Open job" → user applies there (extension side panel offers copy buttons) → "I applied".
- **Assisted (extension on allowed ATS):** open job page → extension shows fit + "Fill form" →
  fields filled, unknown questions highlighted → user reviews and submits → proof recorded →
  pipeline updates.
- **Automatic (server-side, opt-in after dry-run review):** queued → dry-run preview available →
  submitted within caps → toast + pipeline update; proof in application detail.

### J4 — Unknown screening question
Question appears on Today (and as a notification) → user answers inline, picks scope (this
company / this market / everywhere) → application resumes; answer saved to the bank.

### J5 — Interview to offer
Email detected → "Interview with Demo Airlines on Tuesday" notification → **celebration** on first
view → Interview prep pack → after interview: outcome → offer email → offer figures → **Offer
comparison** across currencies → decision (hired/declined).

### J6 — Weekly review (Sunday evening)
Weekly report → Insights (callback rate by source/market/CV variant) → re-plan proposal diff →
approve or reject.

### J7 — Privacy check
Settings → Privacy → see each connection with what we read/store → revoke Gmail (immediate) or
export data / delete account.

### J8 — Operator: connector degraded (admin)
Ops alert (Telegram ops chat) → Admin → Connectors → "Bayt alerts parser degraded" → open runbook →
replay unparsed messages after the fix.

## 5. Screens

Format per screen: **Purpose · Layout · Hierarchy · Interactions · Motion · States ·
Accessibility/RTL · Stories/endpoints.**

### 5.1 Landing page (public, Stage 3)
**Purpose:** explain JobRadar in one screen and get a sign-up (or invite request).

```
┌────────────────────────────────────────────────────────────────┐
│ [logo] JobRadar                    How it works  Privacy  Sign in │
├────────────────────────────────────────────────────────────────┤
│  Your calm co-pilot for the job search.          ┌───────────┐  │
│  Find the right jobs in any country, apply       │ live demo │  │
│  without the busywork, and never lose track.     │ job card  │  │
│  [ Get started ]  [ See how it works ]           │ + score   │  │
│                                                  └───────────┘  │
├────────────────────────────────────────────────────────────────┤
│  1 Discover  →  2 Match with reasons  →  3 Apply safely  →  4 Track │
├────────────────────────────────────────────────────────────────┤
│  Built for everyone: nurses · engineers · teachers · movers …  │
│  Privacy promises (3 cards)    ·   No spam to employers (rules) │
├────────────────────────────────────────────────────────────────┤
│  FAQ  ·  Footer: privacy, terms, grievance contact, language    │
└────────────────────────────────────────────────────────────────┘
```
- **Hierarchy:** headline → one primary CTA → product proof (a real, animated JobCard with the
  ScoreRing and "why") → 4-step strip → trust (privacy, fair use) → FAQ.
- **Interactions:** language switcher (incl. Arabic → RTL), theme follows system.
- **Motion:** hero card score reveal once on view; steps fade in on scroll (reduced motion: none).
- **States:** static page; invite-only stage shows "Request an invite" form with success state.
- **A11y/RTL:** one `h1`; illustration `aria-hidden`; mirrored step arrows in RTL.
- **Performance:** prerendered static HTML, LCP < 2.5 s on 4G, Lighthouse ≥ 90 (PRD E10).
- **Stories:** US-11.1.

### 5.2 Sign up / Sign in
**Purpose:** quick, trustworthy account access.

```
┌──────────────── centered card (max 420 px) ────────────────┐
│ [logo]  Create your account                                │
│ [ Continue with Google ]                                   │
│ ─────────────── or ───────────────                         │
│ Email      [                          ]                    │
│ Password   [                          ] (show)  strength ▂▃▅│
│ Invite code [            ] (Stage 2 only)                  │
│ ☐ I agree to the Terms and Privacy Policy (links)          │
│ [ Create account ]                                         │
│ Already have an account? Sign in                           │
└────────────────────────────────────────────────────────────┘
```
- **Sign in:** email + password, Google, "Forgot password?"; admin/owner continue to a TOTP step
  (6-digit code input with auto-advance and paste support).
- **Interactions:** inline validation on blur; password show/hide; Enter submits.
- **Motion:** card fade-rise on load; error shake is **not** used (calm) — errors appear inline
  with an icon.
- **States:** loading (button spinner), invalid credentials ("Email or password is incorrect" —
  never says which), locked/rate-limited ("Too many attempts. Try again in 15 minutes."),
  signup closed (explains invite-only), verify-email sent (with resend after 60 s).
- **A11y:** labels visible (no placeholder-only), errors linked via `aria-describedby`, TOTP
  input is one field with `autocomplete="one-time-code"`.
- **Stories/endpoints:** US-4.2, US-10.1 · `/auth/*`.

### 5.3 Onboarding wizard
**Purpose:** go from zero to useful matches in ~5 minutes, adapted by persona.

```
┌ Stepper: ① Resume ② Review ③ Markets & roles ④ Channels & privacy ⑤ Applying ┐
├───────────────────────────────────────────────────────────────────────────────┤
│ ② Review what we found                                    Step 2 of 5        │
│ ┌ Draft from your resume ─────────────────┐ ┌ Source ──────────────────────┐  │
│ │ Current title  Senior Software Engineer ✎│ │ …led migration of payment   │  │
│ │ Years          6.5                      ✎│ │ services to **Spring Boot** │  │
│ │ Skills  [Java ×][Spring ×][Kafka ×] +add │ │ (highlighted source span)   │  │
│ │ ⚠ Not found: notice period — add it      │ └─────────────────────────────┘  │
│ └──────────────────────────────────────────┘                                  │
│                                   [ Back ]                  [ Looks right → ] │
└───────────────────────────────────────────────────────────────────────────────┘
```
- **Steps:**
  1. **Resume:** drag-and-drop PDF/DOCX or "Fill in manually". Upload progress, then parsing
     skeleton.
  2. **Review:** every extracted field shows its source text on focus (facts-only, ADR-0007).
     Missing fields are listed, never guessed.
  3. **Markets & roles:** searchable country picker (enabled markets only, rollout flags),
     role search over title aliases; persona suggestion ("Moving countries? We'll prioritise
     visa-sponsoring roles"); field-specific credential questions ("Do you hold a nursing
     licence recognised in Saudi Arabia?"); per-country visa status.
  4. **Channels & privacy:** digest channels (email on by default, push, Telegram link), connect
     job-alert inbox (clear consent card: what we read, what we store, revoke anytime), optional
     extension install.
  5. **Applying:** lanes explained with plain examples; dry-run on; daily caps within plan;
     minimum fit score slider (cannot go below the global floor; tooltip explains why).
  - **Finish:** "First matches" preview (top 5 with reasons); if < 5, one suggested fix.
- **Hierarchy:** one question group per step; progress always visible; Back never loses data.
- **Persona adaptation:** students see "Internships & graduate schemes" and no notice period;
  executives get "Confidential search" (no public profile links, stricter defaults); returners get
  an optional "career break" field (their own words); movers get visa + CV-format steps first.
- **Interactions:** autosave per field; skip optional steps; resume later from Today banner.
- **Motion:** step change = content cross-fade + 8 px slide in reading direction (`duration-slow`);
  stepper check animates on completion.
- **States:** parsing failed (fill manually), unsupported file, inbox connection failed (retry),
  no enabled market for the user's country (explain + "Notify me").
- **A11y/RTL:** stepper is an ordered list with `aria-current="step"`; slide direction mirrors in RTL.
- **Stories/endpoints:** US-10.2, US-1.4, US-10.3 · `/profile/resume`, `/profile/resume/apply`,
  `/onboarding/status`, `/packs/*`, `/consents`, `/inboxes/gmail/connect`.

### 5.4 Today (home)
**Purpose:** the 5–15 minute daily session: what needs me, what's new, what's next.

```
Desktop                                                           Phone
┌ Good morning, Asha.  6 new matches · 1 question · 1 interview ┐ ┌ Good morning ────┐
├───────────────────────────────────────┬───────────────────────┤ │ 6 new · 1 Q · 1 I │
│ ⓘ Needs you (1)                        │ Next up               │ │ ⓘ Needs you      │
│ ┌ Question from Example Co ─────────┐ │ ┌ Interview Tue 10:00┐ │ │ [question card]  │
│ │ "Do you need visa sponsorship?"   │ │ │ Demo Airlines      │ │ │ Top matches      │
│ │ ( ) Yes  ( ) No   Save for: [UAE▾]│ │ │ [Open prep pack]   │ │ │ [JobCard swipe]  │
│ └───────────────────────────────────┘ │ └────────────────────┘ │ │ Next up          │
│ Top matches today                     │ This week              │ │ [interview]      │
│ [JobCard] [JobCard] [JobCard]         │ 2 interviews · ▁▃▅█   │ │ This week        │
│ [See all 6 →]                         │ Usage: 3/8 auto today  │ └──────────────────┘
│ Waiting on you: 1 one-tap pack        │                        │
└───────────────────────────────────────┴───────────────────────┘
```
- **Hierarchy:** greeting with counts → **Needs you** (questions, one-tap packs, needs_review,
  reconnect inbox) → **Top matches** (3, expanded JobCards with "why" and pay) → **Next up**
  (interviews, deadlines, follow-ups due) → **This week** (north-star sparkline: interviews/week,
  usage meter).
- **Interactions:** answer questions inline; Apply/Skip/Save on cards (keyboard `a/x/s`); swipe on
  phones; "All caught up" collapses sections that are empty.
- **Motion:** sections fade-rise with a small stagger; answered question collapses
  (`duration-base`) and a toast confirms "Saved — applying to Example Co".
- **States:** loading skeletons for each section; empty → "All caught up. We'll check again at
  10:00." + "Broaden search"; paused → banner "Applying is paused" + Resume; scoring delayed badge;
  offline cached.
- **Stories/endpoints:** US-4.3, US-4.4, US-5.4, US-9.1 · `/digest/today`, `/questions`,
  `/matches`, `/me/status`, `/me/usage`.

### 5.5 Job feed
**Purpose:** browse, filter and act on all matches quickly.

```
┌ Jobs  [Matches 42] [Possible 18] [Saved 7]        [ Search jobs, companies… ] ┐
│ Filters: Market [UAE ✓][India ✓] · Fit ≥ [70] · Remote ▾ · Visa ▾ · Posted ▾ │
├──────────────────────────────────────────┬───────────────────────────────────┤
│ ● 86  Senior Java Backend Engineer   UAE │ (xl: detail pane = Job detail)    │
│       Fictional Logistics · Dubai · 2d   │                                   │
│       ✓ Visa sponsored  AED 22k/mo       │                                   │
│       [Apply] [Save] [Skip]              │                                   │
│ ● 81  Backend Engineer (Java)      India │                                   │
│ …                                        │                                   │
└──────────────────────────────────────────┴───────────────────────────────────┘
```
- **Tabs:** Matches (Tier 2 scored, ranked), Possible (Tier 1 "possible match" with "Score this
  job" on demand, budget-counted), Saved.
- **Hierarchy:** fit score (ring + number) → title → company/location/age → eligibility
  highlight → pay → actions. Ineligible jobs are hidden by default; a toggle "Show 12 not
  eligible" lists them with reasons (transparency).
- **Interactions:** instant filters in URL; `j/k` navigation; Enter opens detail (side pane on xl,
  sheet on md, page on phone); bulk select for Skip/Save only (never bulk Apply — anti-spam);
  swipe right = Apply, left = Skip, with buttons as the accessible alternative.
- **Motion:** list items enter with ≤ 6-item stagger; skipped card collapses with height animation
  + Undo toast; score rings reveal once per session.
- **States:** skeleton rows; empty matches → explain filters + "Reset filters"; no results for
  search; "Scoring delayed" badge; budget exhausted → banner explaining rules-only ranking.
- **Stories/endpoints:** US-3.4, US-3.7, US-4.3 · `/matches`, `/matches/possible`,
  `/jobs/{job_id}/score|apply|skip|save`.

### 5.6 Job detail
**Purpose:** decide with confidence: why it fits, whether I'm eligible, what it pays, how to apply.

```
┌ ← Jobs                                                     [Save] [Skip] [Apply ▸] ┐
│ Senior Java Backend Engineer                                    ◯ 86 fit           │
│ Fictional Logistics Co · Dubai, UAE · Hybrid · Posted 2 days ago · via Greenhouse  │
├───────────────────────────────────┬────────────────────────────────────────────────┤
│ Why it fits                       │ Eligibility                                    │
│ ✓ Java, Spring Boot, Kafka (6/7)  │ ✓ Visa sponsorship offered (high confidence)   │
│ ✕ Missing: Kubernetes (preferred) │ ✓ Experience 5–8 yrs (you: 6.5)                │
│ Rationale paragraph (LLM, text)   │ ⚠ Prefers 30-day notice (you: 60)              │
│ Score breakdown ▸ fit 86 · fresh  │                                                │
├───────────────────────────────────┼────────────────────────────────────────────────┤
│ Pay comparison                    │ How you'll apply                               │
│ AED 22,000 /mo (tax-free)         │ Lane: Assisted (extension) · dry-run on        │
│ ≈ ₹5,02,000 /mo at 22.8 (30 Oct)  │ CV: UAE format · photo off  [Change toggles]   │
│ vs India in-hand ₹2,18,000 /mo    │ 2 questions known · 1 unknown                  │
│ Assumptions ▸                     │                                                │
├───────────────────────────────────┴────────────────────────────────────────────────┤
│ Job description (untrusted text, rendered as plain text, collapsible)              │
│ Was this match good?  👍 👎                                                         │
└───────────────────────────────────────────────────────────────────────────────────┘
```
- **Hierarchy:** title + fit → actions (sticky on scroll; bottom bar on phones) → **Why** and
  **Eligibility** side by side → **Pay** → **How you'll apply** → description → feedback.
- **Interactions:** "Why not 100?" expands the score breakdown; "Assumptions" shows FX rate + date,
  tax regime, deductions; CV field toggles (photo, DOB, marital status) only if supplied; Apply
  opens the lane-specific flow (one-tap pack sheet / extension hint / queue confirmation).
- **Motion:** sheet slide-in from inline-end (`duration-slow`); score reveal; Apply button morphs
  to "Applied ✓" with success toast.
- **States:** expired job (banner, actions disabled, "Find similar"); ineligible (reasons first,
  Apply disabled with explanation); unscored (Tier 1) with "Score this job"; salary not disclosed
  ("Not disclosed — we never estimate it"); stale FX badge; description failed to load.
- **A11y/RTL:** description `lang` set if detected; Latin terms in Arabic UI isolated with `<bdi>`.
- **Stories/endpoints:** US-3.2, US-3.3, US-3.5, US-5.1, US-5.5 · `/jobs/{job_id}`,
  `/jobs/{job_id}/explain`, `/jobs/{job_id}/feedback`.

### 5.7 Pipeline board
**Purpose:** see and manage every application by state.

```
┌ Pipeline   [Search] [Lane ▾] [Market ▾]                       Board | List ┐
│ Queued (4)    Applied (12)   Acknowledged (3)  Assessment (1)  Interview (2)  Offer (1) │
│ ┌────────┐   ┌────────┐      ┌────────┐        ┌────────┐      ┌────────┐     ┌──────┐ │
│ │Example │   │Demo Air│      │ …      │        │ HackerR│      │Demo Air│     │ Sample│ │
│ │⏳ answer│   │3d · 1tap│     │        │        │due Fri │      │Tue 10:00│    │ AED… │ │
│ └────────┘   └────────┘      └────────┘        └────────┘      └────────┘     └──────┘ │
│ Closed ▸ (rejected 5 · ghosted 4 · withdrawn 1 · skipped 30)                           │
└─────────────────────────────────────────────────────────────────────────────────────┘
```
- **Columns:** active states in order; closed states collapsed into a "Closed" drawer. Phone: one
  column at a time with a segmented state selector and swipe between columns.
- **Card:** company, title, lane icon, last event age, sub-state chip (`awaiting_answer`,
  `needs_review`, `awaiting_user`), next deadline.
- **Interactions:** drag and drop between columns for **user-allowed transitions only**
  (state-machine.md §4); invalid targets dim while dragging and show why on hover ("Offers come
  from the employer — add one from the email or 'Add offer'"); keyboard DnD (Space, arrows,
  Space); "Move to…" menu as the non-drag alternative; optimistic move with `expected_from` and
  rollback + toast on conflict; Undo for withdraw.
- **Motion:** FLIP card move (`duration-slow`, gentle); column counts tick; moving a card to
  **Interview** or **Offer** triggers the **celebration** (once per event).
- **States:** empty board → "No applications yet — apply to your first match"; loading
  skeleton columns; offline (read-only, moves queued); `needs_review` card highlighted with
  warning chip.
- **Stories/endpoints:** US-6.5 · `/applications`, `/applications/{application_id}/transition`,
  `/events/{event_id}/undo`.

### 5.8 Interview prep
**Purpose:** walk into each interview prepared, with facts from the user's own history.

```
┌ Interview · Demo Airlines · Senior Backend Engineer · Round 2 (Technical)       ┐
│ Tue 4 Nov, 10:00 GST (12:30 your time) · [Join link] · [Add to calendar (.ics)] │
├───────────────────────────────┬──────────────────────────────────────────────────┤
│ Checklist                     │ Prep pack                                        │
│ ☑ Read job description         │ What they assess: API & system design, Java     │
│ ☐ Review your 3 stories        │ Your relevant stories (from your profile):       │
│ ☐ Practise system design       │  • Payments migration (source: experience #2)    │
│                               │ Likely questions (role pack) ▸                   │
│ Notes [                     ] │ Company notes (from public info you saved) ▸     │
└───────────────────────────────┴──────────────────────────────────────────────────┘
│ After the interview: How did it go?  [Passed to next round] [Waiting] [Not selected] │
```
- **Hierarchy:** when/where (time in both zones) → checklist → prep pack → outcome capture.
- **Interactions:** checklist persists; notes autosave; outcome buttons create the next round or
  transition state; prep pack regenerate (budget-counted).
- **Motion:** checklist ticks animate (`duration-fast`); celebration on first view of a new
  interview (from the pipeline/notification).
- **States:** prep pack generating (skeleton) / failed (retry) / not yet generated ("Prepare for
  me"); past interview (read-only + outcome).
- **Stories/endpoints:** US-9.3 · `/interviews`, `/interviews/{interview_id}/prep-pack`.

### 5.9 Offer comparison
**Purpose:** compare offers fairly across currencies, periods and tax systems.

```
┌ Offers                                         Compare in: [INR ▾]  per [month ▾] ┐
│                     Sample Retail (India)   Demo Airlines (UAE)    Current job   │
│ Base               ₹28,00,000 /yr          AED 18,000 /mo          ₹22,00,000/yr │
│ Allowances         —                       Housing 4,000 · Transp. 1,000          │
│ Variable / bonus   10 %                    —                                      │
│ Tax                New regime (est.)       0 %                                    │
│ In-hand / month    ₹1,82,000               ₹5,02,000 (≈ AED 22,000)               │
│ Joining · deadline 1 Dec · 10 Nov          15 Jan · 7 Nov ⚠                       │
│ ▁▃█ comparison bars (in-hand, same scale)                                         │
│ Assumptions: AED→INR 22.8 (30 Oct, manual) · India new regime · PF 12 % …  Edit ▸ │
│ Your adjustments: rent difference [      ] /mo · flights home [     ] /yr          │
│ [Accept offer] [Decline]                                                          │
└──────────────────────────────────────────────────────────────────────────────────┘
```
- **Hierarchy:** in-hand per month (the comparable number) is the highlighted row; every derived
  value has an assumptions link; user adjustments are clearly labelled "your numbers".
- **Interactions:** switch comparison currency/period; edit offer figures inline; add current job
  as a baseline; Accept → `hired` (suggests pausing all lanes), Decline → `declined`.
- **Motion:** bars animate to new values on currency switch (`duration-slow`); offer arrival
  triggers celebration once.
- **States:** single offer (compare with current job prompt); missing figures ("Add base salary to
  compare"); stale FX badge; deadline near (warning chip, not red until past).
- **Stories/endpoints:** US-9.4 · `/offers`, `/offers/compare`.

### 5.10 Insights
**Purpose:** learn what works; see progress toward interviews.

```
┌ Insights  Range: [Last 30 days ▾]   Compare: [previous period]                ┐
│ Interviews / week  2.0 ▲0.5   Callback rate 12 % ▲2   Applications/wk 18   Ghosting 22 % │
├─────────────────────────────────────┬────────────────────────────────────────┤
│ Funnel                              │ Callback rate by source                │
│ Discovered ████████████ 1,240       │ Company ATS   ███████ 18 %             │
│ Matched    ██████ 310               │ Alerts (UAE)  █████ 13 %               │
│ Applied    ██ 72                    │ One-tap       ███ 8 %                  │
│ Interview  ▌ 9 · Offer ▏ 1          │ [View as table]                        │
├─────────────────────────────────────┼────────────────────────────────────────┤
│ Weekly progress (interviews)        │ By CV variant · by market · by lane    │
├─────────────────────────────────────┴────────────────────────────────────────┤
│ This week's suggestions: "UAE alerts convert better than India aggregators —   │
│ shift 2 daily applications" [Review plan change]                               │
└──────────────────────────────────────────────────────────────────────────────┘
```
- **Hierarchy:** north star first (interviews/week), then supporting KPIs, funnel, breakdowns,
  suggestions (linked to the re-plan proposal).
- **Interactions:** range and comparison pickers; chart hover/focus tooltips; "View as table" on
  every chart; click a bar to filter the pipeline.
- **Motion:** bars grow on first render (`duration-slow`, stagger), numbers count up once.
- **States:** not enough data ("Insights appear after ~2 weeks of applications"), loading chart
  skeletons, partial (late events) note.
- **Stories/endpoints:** US-9.1, US-9.2, US-9.5 · `/insights/*`, `/plan/proposals`.

### 5.11 Settings
**Purpose:** control everything, with plain explanations next to each control.

Sections (left list on desktop, stacked list on phone):
1. **Profile** — facts with inline editing; sensitive fields (photo, DOB, marital status,
   nationality) grouped under "Optional personal details" with "off by default in CVs" note.
2. **Documents** — CV variants per market/role, default field toggles, preview DOCX/PDF.
3. **Answers** — answer bank with search, scope chips, last used.
4. **Markets & roles** — targets, visa status per country, credentials per market.
5. **Applying** — lanes (one-tap / assisted / automatic) with status, daily caps (plan-bounded),
   minimum fit (≥ global floor), dry-run review record, **Pause all**.
6. **Notifications** — per event × channel matrix, quiet hours, digest time.
7. **Connections** — alert inbox (Gmail / forwarding address), Telegram, browser extension,
   home runner (advanced, off), each with status, consent and Disconnect.
8. **Privacy** — what we store and why (data map summary), consents history, export data,
   delete account (typed confirmation + grace period).
9. **Appearance** — theme (system/light/dark), language, reduced motion, keyboard shortcuts on/off.
10. **Plan & usage** — plan limits, usage meters with reset times.

- **Interactions:** autosave with "Saved" inline confirmation; switches for instant settings;
  destructive actions in a separate "Danger zone" card.
- **States:** connection errors ("Gmail needs reconnecting" with button); export in progress →
  ready (download until expiry); deletion scheduled banner with "Cancel deletion".
- **Stories/endpoints:** US-1.1, US-1.3, US-4.4, US-4.5, US-5.1, US-10.3, US-10.5, US-10.7 ·
  `/profile`, `/answers`, `/resume-variants`, `/notification-prefs`, `/consents`, `/inboxes`,
  `/tokens`, `/me/*`.

### 5.12 Browser extension
**Popup** (toolbar button, 360 × 520 px):
```
┌ [logo] JobRadar            ● Connected ┐
│ This page                               │
│ ┌ Senior Java Backend Engineer ◯ 86 ┐   │   (allowed ATS host only)
│ │ ✓ Eligible · AED 22k/mo           │   │
│ │ [ Fill form ]  [ Open in JobRadar ]│   │
│ └───────────────────────────────────┘   │
│ [ Save this job ]  (URL + title only)   │
│ Your queue (3)  ▸                       │
│ Paused? No · Today 3/8 assisted         │
└─────────────────────────────────────────┘
```
- On **one-tap-only hosts** (LinkedIn, Indeed, Gulf boards) the "This page" card is replaced by
  "JobRadar doesn't read or fill this site. Open the side panel to copy your prepared answers." and
  **Open side panel**.

**Side panel** (browser side panel, extension UI only):
```
┌ One-tap pack · Demo Airlines (LinkedIn) ┐
│ Pick job: [ My one-tap queue ▾ ]        │
│ CV: UAE format  [Download]              │
│ Cover note  [Copy]                      │
│ "Years of Java?" → "6.5"       [Copy]   │
│ "Notice period?" → "60 days"   [Copy]   │
│ [ I applied ]   [ Skip ]                │
└─────────────────────────────────────────┘
```
**In-page assist** (allowed ATS pages only): fields JobRadar filled get a subtle `primary-soft`
outline; unknown questions get a `warning` outline and an "Answer in JobRadar" chip; a small
floating bar says "Review everything, then submit yourself." The extension never clicks submit.

- **Motion:** copy buttons flip to "Copied ✓" for 1.5 s; filled fields fade their highlight in
  sequence (≤ 30 ms stagger).
- **States:** not paired (Connect flow: "Open JobRadar to connect"), token expired (re-pair),
  outdated version (update prompt, HTTP 426), host permission not granted (explain + "Allow on
  this site"), paused/cap reached (assist disabled with reason), offline.
- **A11y/RTL:** popup and side panel follow the user's locale and direction.
- **Stories/endpoints:** US-8.2, US-8.3 · `/ext/*`, `/auth/pair/*`.

### 5.13 Admin console (admin/owner, MFA-verified)
**Purpose:** keep the system healthy without seeing user content.

```
┌ Admin  System | Connectors | Queues | Flags | Rollout | Users | Abuse | LLM | Audit ┐
│ System health: API ● · Workers ● · Queue depth 12 · Dead letters 2 · Paused: no    │
│ Connectors                                                                       │
│ Source            Last run   Status     Found/New   7-day trend   Action          │
│ greenhouse        08:00      ● ok       420/18      ▁▃▂▅▃▄▅       [Runs]          │
│ alerts:bayt       08:02      ▲ degraded 0/0         ▅▅▄▅▅▁▁       [Runbook][Replay]│
├──────────────────────────────────────────────────────────────────────────────────┤
│ Rollout: India ● enabled · UAE ● enabled · Saudi Arabia ◐ 5/8 checklist [Open]    │
│ LLM: cost/MAU $0.13 (target ≤ $0.20) · Tier 2 coverage 93 % · budget 41 % used    │
└──────────────────────────────────────────────────────────────────────────────────┘
```
- **Hierarchy:** health summary → problems first (degraded connectors, dead letters, abuse
  signals) → tabs for detail.
- **Interactions:** DataTables with filters; replay/discard dead letters (confirm); flag edits with
  reason (audit); market flag toggle **refuses** unless conformance is green (shows failing
  checks); user directory without content; content view only with active support grant (banner
  shows grant expiry); abuse review actions (dismiss, cool-down, suspend) with reason.
- **Motion:** minimal (admin is a tool): row updates highlight briefly in `primary-soft`.
- **States:** all healthy ("All systems normal"), loading tables, permission denied (MFA required),
  empty dead letters.
- **Stories/endpoints:** US-2.6, US-4.6, US-10.6, US-10.8, US-10.10 · `/admin/*`.

## 6. Channels

### 6.1 Daily digest (email, web push, Telegram)
Built once (`build_digest`), rendered per channel and locale (notify LLD).

**Email** (HTML + plain text; 600 px; tokens mapped to inline styles; dark-mode friendly):
```
JobRadar · Good morning — 6 new matches
1 question needs you → [Answer]
Top matches
  86 · Senior Java Backend Engineer · Fictional Logistics · Dubai
     ✓ Visa sponsored · AED 22,000/mo · "6 of 7 core skills match"
     [Apply] [Save] [Skip]            (signed action links)
  …
Next up: Interview Tue 10:00 (Demo Airlines) → [Prep pack]
Manage notifications · Pause applying · Privacy
```

**Web push** (short, one deep link): "6 new matches · 1 question needs you" → opens Today.
Interview/offer pushes are separate and never batched.

**Telegram** (compact, buttons; pay hidden unless `telegram_show_pay`):
```
☀️ Good morning — 6 new matches, 1 question

86 · Senior Java Backend Engineer
Fictional Logistics · Dubai 🇦🇪 · visa sponsored
Why: 6 of 7 core skills match
[✅ Apply] [💾 Save] [⏭ Skip] [🔎 Open]

…(top 5)…
❓ Example Co asks: "Do you need visa sponsorship?"
[Yes] [No] [Answer in app]

/pause · /status · /today · /stats
```
- Empty digest says why ("No new eligible jobs since yesterday. We'll keep looking.").
- Quiet hours respected; delivery by 08:15 local (SLO).
- **Stories:** US-4.4, US-4.5, US-5.4.

## 7. Accessibility and localization checklist (every screen)
- Keyboard path for every action, including DnD and swipe alternatives; visible focus.
- Screen reader names for ScoreRing ("Fit 86 of 100"), icons, charts (table alternative).
- LTR and RTL screenshots in visual regression; mirrored directional icons; `<bdi>` for mixed text.
- Locale formatting for money, dates, times (with time zone for interviews), numbers.
- Reduced motion honoured (system and in-app).
- Text expansion +40 % without truncating essential information.

## 8. Open UX questions
1. Mobile swipe gestures: on by default for everyone, or offered after the first session? (Proposed:
   on, with a one-time hint and buttons always visible.)
2. Should "Possible matches" be shown on Today, or only in Jobs? (Proposed: Jobs only, to keep
   Today calm.)
3. Email digest images (company logos) are off to avoid tracking pixels and hotlinking; confirm.
