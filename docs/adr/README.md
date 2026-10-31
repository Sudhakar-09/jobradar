# Architecture Decision Records

One file per significant decision, numbered in order. Format: [`template.md`](template.md).

- Status values: `Proposed`, `Accepted`, `Superseded by ADR-NNNN`, `Deprecated`.
- Never rewrite an accepted ADR's decision. Supersede it with a new ADR and link the two
  both ways.
- Each ADR links the `docs/decisions-log.md` entry it records.

| ADR | Title | Status |
|---|---|---|
| [0001](0001-modular-monolith.md) | Modular monolith | Accepted |
| [0002](0002-home-runner-for-logged-in-portals.md) | Home runner for logged-in portals | Accepted; amended by 0016 |
| [0003](0003-one-tap-lanes-for-linkedin-indeed-gulf-boards.md) | One-tap lanes for LinkedIn, Indeed and Gulf boards | Accepted |
| [0004](0004-private-repository.md) | Private repository | Accepted |
| [0005](0005-checkout-outside-onedrive.md) | Checkout at `C:\dev\jobradar`, outside OneDrive | Accepted |
| [0006](0006-pluggable-markets-india-uae-first.md) | Pluggable markets; India + UAE, Java Backend first | Accepted; amended by 0013 |
| [0007](0007-yaml-profile-and-facts-only-parsing.md) | YAML profile, PyYAML, facts-only resume parsing | Accepted |
| [0008](0008-gmail-job-alerts-as-main-uae-source.md) | Gmail job-alert ingestion as main UAE source (Phase 2) | Accepted |
| [0009](0009-compensation-comparison-fx-and-tax-defaults.md) | Compensation comparison: manual dated FX, USD peg, India new regime default | Accepted |
| [0010](0010-uae-cv-field-defaults.md) | UAE CV field defaults with per-application toggle | Accepted |
| [0011](0011-celery-queues-and-idempotent-tasks.md) | Celery with per-domain queues and idempotent tasks | Accepted |
| [0012](0012-layered-modules-enforced-by-import-linter.md) | Layering api → services → repositories → models | Accepted |
| [0013](0013-product-for-everyone.md) | Product for everyone; staged rollout | Accepted |
| [0014](0014-web-app-stack-replaces-streamlit.md) | Web app stack; Streamlit removed | Accepted |
| [0015](0015-design-system-tokens-and-visual-quality-gates.md) | Design system, tokens and visual quality gates | Accepted |
| [0016](0016-browser-extension-default-runner-optional.md) | Browser extension by default; home runner optional | Accepted |
| [0017](0017-auth-sessions-and-tenant-isolation.md) | Auth, sessions, scoped tokens and tenant isolation | Accepted |
| [0018](0018-privacy-consent-and-email-access.md) | Privacy, per-source consent and email access strategy | Accepted |
| [0019](0019-quotas-budgets-and-anti-abuse.md) | Quotas, LLM budgets, plans and anti-abuse | Accepted |
| [0020](0020-i18n-rtl-and-fonts.md) | Internationalization, RTL and fonts | Accepted |
| [0021](0021-role-taxonomy-and-credentials.md) | Role taxonomy, field documents and credentials | Accepted (licensing check open) |
| [0022](0022-source-policy-registry.md) | Source policy registry governs automation per host | Accepted |
| [0023](0023-tiered-matching-and-llm-cost-target.md) | Tiered matching pipeline and LLM cost target | Accepted |
| [0024](0024-market-and-role-quality-gates.md) | Market and role quality gates, synthetic users and rollout flags | Accepted |
