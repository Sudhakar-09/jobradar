# LLD — Packs and source policies (`core.packs`, `core.source_policies`)

| | |
|---|---|
| Status | Implemented (Phase 2a, 2026-10-30) |
| Owner module | `core` (configuration infrastructure; every domain may read it) |
| PRD stories | US-1.2 (AC1–AC3), US-2.8 |
| ADRs | ADR-0006, ADR-0010, ADR-0013, ADR-0021, ADR-0022, ADR-0024 |

## 1. Responsibilities
- Define and validate the **market, role and persona pack** schemas (PRD §4.1–§4.3) and load the
  YAML files in `packs/`.
- Define and load the **source policy registry** (`config/source_policies.yaml`, ADR-0022) and
  answer "what may JobRadar do on this host?".
- Warn when a pack's facts are unverified or older than 90 days.
- Cross-check that a market pack never claims an access mode its sources' policies don't grant.

**Must NOT do:** fetch anything over the network; contain market-, role- or host-specific
branches; decide eligibility or pay (that is matching / normalizer using these packs).

## 2. Public interface

```python
# jobradar.core.packs
class MarketPack(PackModel):       # code, name, kind, country_codes, money: Money,
                                   # locales: list[LocaleSpec], default_locale, cv: CvNorms,
                                   # visa_routes, sponsor_register_source,
                                   # nationality_restricted_programmes, sources: list[MarketSource],
                                   # notice_period_norm, hiring_seasons, language_notes,
                                   # credential_recognition, provenance: Provenance
    currency: str                  # property: money.currency
    rtl: bool                      # property: any locale is right-to-left
class RolePack(PackModel):         # code, field, family, isco_08, title_aliases,
                                   # title_aliases_by_locale, core_skills, adjacent_roles,
                                   # signal_documents, required_credentials, valued_credentials,
                                   # hiring_patterns: HiringPatterns, resume_emphasis, provenance
class PersonaPack(PackModel):      # code, description, channel_weights, daily_volume_range,
                                   # tailoring_depth, resume_strategy, onboarding_steps,
                                   # followup_days, default_llm_top_n, default_min_fit_score, tips
SENSITIVE_CV_FIELDS: frozenset[CvField]   # photo, date_of_birth, marital_status

def load_market_pack(path: Path) -> MarketPack: ...
def load_role_pack(path: Path) -> RolePack: ...
def load_persona_pack(path: Path) -> PersonaPack: ...
def load_market_packs(directory: Path) -> list[MarketPack]: ...   # unique codes enforced
def load_role_packs(directory: Path) -> list[RolePack]: ...
def load_persona_packs(directory: Path) -> list[PersonaPack]: ...
def source_policy_problems(market: MarketPack, registry: SourcePolicyRegistry) -> list[str]: ...

# jobradar.core.source_policies
class AccessMode(StrEnum): API, ATS_FEED, ALERT_EMAIL, EXTENSION_ASSIST, SERVER_APPLY, ONE_TAP,
                           LOGO_FETCH, NONE
class SourcePolicy(BaseModel):     # id, name, hosts (exact or "*.domain"), company_domains,
                                   # modes, rate_limit (per_minute, burst, per_day), docs_url,
                                   # terms_url, notes, last_reviewed
class SourcePolicyRegistry:
    def policy_for(self, host: str) -> SourcePolicy: ...   # exact > wildcard > one-tap default
    def is_allowed(self, host: str, mode: AccessMode) -> bool: ...
    def hosts_with_mode(self, mode: AccessMode) -> frozenset[str]: ...
    def get(self, policy_id: str) -> SourcePolicy: ...
def load_source_policies(path: Path) -> SourcePolicyRegistry: ...
```

`connectors` re-exports `policy_for`, `assert_allowed` and `hosts_with_mode` as its public
service functions (connectors LLD §2); other domains use those, not the registry directly.

## 3. Validation rules (schema-level)

| Pack | Rule |
|---|---|
| Market | ISO currency and country codes; default period/basis among the quoted ones; a country market has one country code; `default_locale` is one of `locales`; each locale's `rtl` matches its language; **sensitive CV fields can never be on by default**; no field both on and off; page range valid; unique source codes; unknown keys rejected |
| Role | ISCO-08 code format; at least one title alias; unique credential codes |
| Persona | channel weights non-negative and sum to 1; volume range ordered; follow-up days increasing and positive; top N 1–50; minimum fit 0–100 |
| Source policy | host pattern format; `none` cannot combine with other modes; needs hosts or `company_domains`; company domains may only use `logo_fetch`; a host pattern belongs to one policy; unique ids |
| Cross-file | `source_policy_problems`: a market source's access modes ⊆ the modes its hosts' policies allow (test now; conformance suite in 2h) |

## 4. Data owned
Files only: `packs/markets/*.yaml`, `packs/roles/*.yaml`, `packs/personas/*.yaml`,
`config/source_policies.yaml`. No tables.

## 5. Errors, config, logs
- Invalid pack → `pydantic.ValidationError` with the field path; non-mapping file → `ValueError`.
  Both stop startup (packs are validated at load).
- Log events: `packs.verification_missing {pack_kind, pack}`,
  `packs.verification_stale {pack_kind, pack, last_verified}`.
- Constant: `PACK_STALE_AFTER = 90 days` (CLAUDE.md §8).

## 6. Test plan (implemented)
`tests/unit/core/test_packs.py` and `tests/unit/core/test_source_policies.py`: repository packs
load; UAE owner decisions (monthly AED package, no income tax, RTL locale, Naukrigulf and other
Gulf boards as alert-email + one-tap, CV defaults); every invalid-value rule above; stale and
missing verification warnings; LinkedIn/Indeed/Gulf boards never get automation modes; unknown
hosts are one-tap only; ATS boards have feeds but no `server_apply`; extension-assist host list
excludes one-tap platforms; registry conflicts.

## Dated market data (added 2026-10-31)

Figures that change on a schedule (visa salary thresholds now; tax tables in Phase 3) live in
`config/market_data/<market>/<table>.yaml`, not in packs, and load through `core.dated_data`:
entries with `effective_from`/`effective_to` (no overlaps), a unit (`currency`, `period`,
`basis`), notes for every value key, official `sources` and `last_verified`. A lookup returns the
entry in force on the date or None — values are never extrapolated — and logs
`dated_data.stale` when `last_verified` is older than 90 days or the date is past the newest
entry. A pack visa route points at its table with `salary_thresholds` (e.g. Germany's EU Blue
Card → `germany/eu_blue_card.yaml`); the conformance suite checks that every referenced table
loads and is fresh.
