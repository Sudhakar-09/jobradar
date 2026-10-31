# ARCHIVED — NOT THE SOURCE OF TRUTH.
#
# This script generated the first version of docs/openapi.yaml (2026-10-30, Step 4) from the
# docs/api.md §9 catalogue plus the DTO definitions embedded below. Since the Step 4 review,
# docs/openapi.yaml is the hand-maintained API contract: edit the YAML directly, in a PR that
# states the reason for the contract change. From Phase 4, CI compares it with FastAPI's
# generated schema for shipped phases (docs/api.md §10).
#
# Do not re-run this script over docs/openapi.yaml: it would discard every manual change made
# since. It is kept only as a record of how the initial spec was produced.
"""Generate docs/openapi.yaml from the docs/api.md §9 catalogue plus DTO definitions below.

Usage: uv run python gen_openapi.py <repo_root>
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(sys.argv[1])
API_MD = (ROOT / "docs" / "api.md").read_text(encoding="utf-8")

# ---------------------------------------------------------------- catalogue parsing
section = API_MD.split("## 9. Endpoint catalogue", 1)[1].split("## 10.", 1)[0]
ops = []
current_tag = None
for line in section.splitlines():
    m = re.match(r"### 9\.\d+ (.+)", line)
    if m:
        current_tag = m.group(1).strip()
        continue
    m = re.match(r"\| (GET|POST|PUT|PATCH|DELETE) \| `([^`]+)` \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|$", line)
    if m:
        method, path, purpose, auth, story, phase = m.groups()
        ops.append(dict(method=method, path=path, purpose=purpose.strip(), auth=auth.strip(),
                        story=story.strip(), phase=phase.strip(), tag=current_tag))

TAG_NAMES = {
    "Health (unversioned)": "health",
    "Auth and account (`accounts`)": "accounts",
    "Controls, status and usage": "controls",
    "Packs and legal (read-only)": "packs",
    "Profile, variants, answers, onboarding (`profile`)": "profile",
    "Inboxes, companies, consents (`connectors`, `privacy`)": "inboxes",
    "Matches and jobs (`matching`, `normalizer`)": "matching",
    "Applications, questions, documents (`lifecycle`, `apply`, `documents`)": "applications",
    "Inbox tracking, contacts, interviews, offers (`lifecycle`)": "lifecycle",
    "Notifications and channels (`notify`)": "notify",
    "Strategy and insights (`strategy`, `insights`)": "insights",
    "Privacy (`privacy`)": "privacy",
    "Browser extension (`/ext`, `extension` → `apply`, `connectors`, `lifecycle`)": "extension",
    "Home runner (`/runner`, optional)": "runner",
    "Admin (`/admin`, operational data only)": "admin",
}

# ---------------------------------------------------------------- schema DSL
def ref(name):
    return {"$ref": f"#/components/schemas/{name}"}


PRIMS = {
    "uuid": {"type": "string", "format": "uuid"},
    "str": {"type": "string"},
    "int": {"type": "integer"},
    "num": {"type": "number"},
    "bool": {"type": "boolean"},
    "dt": {"type": "string", "format": "date-time"},
    "date": {"type": "string", "format": "date"},
    "url": {"type": "string", "format": "uri"},
    "email": {"type": "string", "format": "email"},
    "dec": {"type": "string", "pattern": r"^-?\d+(\.\d{1,2})?$", "description": "Decimal as string"},
    "cur": {"type": "string", "pattern": "^[A-Z]{3}$", "description": "ISO 4217 currency"},
    "cc": {"type": "string", "pattern": "^[A-Z]{2}$", "description": "ISO 3166-1 alpha-2"},
    "obj": {"type": "object", "additionalProperties": True},
    "untrusted": ref("UntrustedText"),
    "binary": {"type": "string", "contentMediaType": "application/octet-stream"},
}


def t(spec):
    """Type spec: prim | Ref | [spec] | {spec} (map) | enum:a|b."""
    if spec.startswith("[") and spec.endswith("]"):
        return {"type": "array", "items": t(spec[1:-1])}
    if spec.startswith("{") and spec.endswith("}"):
        return {"type": "object", "additionalProperties": t(spec[1:-1])}
    if spec.startswith("enum:"):
        return {"type": "string", "enum": spec[5:].split("|")}
    if spec in PRIMS:
        return dict(PRIMS[spec])
    return ref(spec)


def nullable(schema):
    if "$ref" in schema:
        return {"anyOf": [schema, {"type": "null"}]}
    s = dict(schema)
    typ = s.get("type")
    if isinstance(typ, str):
        s["type"] = [typ, "null"]
        if "enum" in s:
            s["enum"] = s["enum"] + [None]
    else:
        return {"anyOf": [schema, {"type": "null"}]}
    return s


READ_ONLY = {"id", "created_at", "updated_at"}


def obj(fields, *, request=False, desc=None):
    props, required = {}, []
    for name, spec in fields.items():
        optional = spec.endswith("?")
        spec = spec.rstrip("?")
        schema = t(spec)
        if optional:
            schema = nullable(schema) if not request else schema
        else:
            required.append(name)
        if not request and name in READ_ONLY:
            schema = {**schema, "readOnly": True} if "$ref" not in schema else {"allOf": [schema], "readOnly": True}
        props[name] = schema
    out = {"type": "object", "properties": props}
    if required:
        out["required"] = required
    if request:
        out["additionalProperties"] = False
    if desc:
        out["description"] = desc
    return out


S = {}  # components.schemas


def enum(name, values, desc=None):
    S[name] = {"type": "string", "enum": values}
    if desc:
        S[name]["description"] = desc


def model(name, fields, desc=None):
    S[name] = obj(fields, desc=desc)


def req(name, fields, desc=None):
    S[name] = obj(fields, request=True, desc=desc)


# ---------------------------------------------------------------- enums (database.md / README canonical identifiers)
enum("ApplicationState", ["matched", "queued", "applied", "acknowledged", "assessment", "interview", "offer",
                          "skipped", "failed", "rejected", "ghosted", "withdrawn", "hired", "declined"])
enum("StateReason", ["awaiting_answer", "needs_review", "blocked_by_guard", "cooldown", "awaiting_user"])
enum("Lane", ["auto", "careful", "assisted", "one_tap"])
enum("AppliedVia", ["server", "extension", "runner", "manual"])
enum("Trigger", ["system", "email", "user", "extension", "runner", "admin"])
enum("NotificationEvent", ["digest", "question", "interview_invite", "offer", "followup_due", "weekly_report",
                           "security", "status_change", "reminder", "needs_review", "apply_failed"])
S["ConsentSource"] = {"type": "string",
                      "pattern": r"^(terms|privacy_policy|gmail_alerts|gmail_inbox|forwarding_inbox|extension|telegram|web_push|runner|portal:[a-z0-9.-]+)$",
                      "description": "Canonical consent sources (docs/lld/README.md)."}
enum("GuardCode", ["paused", "lane_disabled", "restricted", "below_quality", "cap_reached", "duplicate",
                   "source_policy", "consent_missing", "deleting"])
enum("Seniority", ["intern", "entry", "junior", "mid", "senior", "lead", "principal", "manager", "director", "executive"])
enum("RemoteType", ["onsite", "hybrid", "remote_country", "remote_region", "remote_global"])
enum("SalaryPeriod", ["hour", "day", "month", "year"])
enum("SalaryBasis", ["gross", "ctc", "package", "basic", "net", "unknown"])
enum("EmploymentType", ["full_time", "part_time", "contract", "temporary", "internship", "freelance"])
enum("Role", ["user", "admin", "owner"])
enum("UserStatus", ["active", "suspended", "pending_deletion"])
enum("VisaSponsorship", ["yes", "no", "unknown"])
enum("EmailClassification", ["acknowledgement", "assessment", "interview_invite", "rejection", "recruiter_outreach", "offer", "other"])
enum("InterviewType", ["screen", "technical", "case", "practical", "panel", "hr", "final", "other"])
enum("InterviewOutcome", ["passed", "failed", "pending", "cancelled"])
enum("ContactRelation", ["recruiter", "hiring_manager", "alumni", "referrer", "other"])
enum("AttemptMode", ["dry_run", "live", "assist", "one_tap"])
enum("AttemptStatus", ["preparing", "awaiting_answer", "filling", "submitting", "submitted", "dry_run_done",
                       "failed", "needs_review", "aborted"])
enum("FieldType", ["text", "textarea", "select", "multiselect", "boolean", "number", "date", "file"])
enum("AnswerScope", ["global", "market", "company"])
enum("Channel", ["in_app", "email", "web_push", "telegram"])
enum("AccessMode", ["api", "ats_feed", "alert_email", "extension_assist", "server_apply", "one_tap", "none"])
enum("DocumentKind", ["cv", "cover_note", "one_tap_pack"])
enum("PlanStatus", ["proposed", "active", "superseded", "rejected"])
enum("ExportStatus", ["queued", "running", "ready", "expired", "failed"])
enum("DeletionStatus", ["scheduled", "running", "completed", "failed"])
enum("AbuseKind", ["burst", "low_response_rate", "employer_report", "duplicate_attempt", "cap_probe"])
enum("RestrictionKind", ["cooldown_automation", "suspend"])
enum("TokenKind", ["extension", "telegram", "runner", "admin_api"])
enum("Browser", ["chrome", "edge", "firefox", "other"])
enum("RunnerTaskKind", ["apply_careful", "check_status"])
enum("RunnerTaskStatus", ["queued", "leased", "done", "failed", "expired"])
enum("InboxKind", ["gmail", "forwarding"])
enum("InboxStatus", ["active", "pending_confirmation", "reauth_required", "revoked"])
enum("SuggestionStatus", ["pending", "accepted", "rejected"])
enum("DeadLetterStatus", ["open", "replayed", "discarded"])
enum("SourceRunStatus", ["running", "ok", "partial", "failed", "degraded"])
enum("ChartName", ["funnel", "callback_rate", "weekly_progress", "salary_comparison"])
enum("LegalDoc", ["privacy_policy", "terms", "consent"])
enum("SignupMode", ["closed", "invite", "open"])
enum("FileKind", ["resume_upload", "rendered_document", "screenshot", "payload_snapshot", "export", "photo"])

# ---------------------------------------------------------------- common
S["UntrustedText"] = {"type": "string", "x-untrusted": True,
                      "description": "Third-party or LLM-derived text. Render as plain text only, never as HTML."}
model("MessageRef", {"key": "str", "params": "obj?"},
      desc="Message key + ICU params; the client renders it in the user's locale.")
model("Money", {"amount": "dec", "currency": "cur", "period": "SalaryPeriod"})
model("ValidationErrorItem", {"field": "str", "key": "str", "params": "obj?"})
S["Problem"] = {
    "type": "object",
    "description": "RFC 9457 problem details, extended with code, detail_key, params and correlation_id.",
    "required": ["type", "title", "status", "code", "correlation_id"],
    "properties": {
        "type": {"type": "string", "format": "uri"},
        "title": {"type": "string"},
        "status": {"type": "integer"},
        "code": {"type": "string", "enum": [
            "bad_request", "unauthenticated", "forbidden", "csrf_failed", "mfa_required", "not_found", "conflict",
            "invalid_transition", "concurrency_conflict", "guard_failed", "precondition_failed", "validation_failed",
            "client_outdated", "consent_required", "rate_limited", "quota_exceeded", "budget_exceeded",
            "upstream_error", "upstream_unavailable", "paused", "internal_error"]},
        "detail_key": {"type": "string"},
        "params": {"type": "object", "additionalProperties": True},
        "correlation_id": {"type": "string", "format": "uuid"},
        "errors": {"type": "array", "items": ref("ValidationErrorItem")},
    },
}
S["CursorPage"] = {"type": "object", "required": ["items", "next_cursor", "has_more"],
                   "properties": {"items": {"type": "array", "items": {}},
                                  "next_cursor": {"type": ["string", "null"]},
                                  "has_more": {"type": "boolean"}}}
model("UndoInfo", {"undo_token": "str", "undo_expires_at": "dt"})
model("SignedFileRef", {"file_id": "uuid", "url": "url", "expires_at": "dt", "content_type": "str", "name": "str?"})
model("Accepted", {"id": "uuid?", "status": "str"}, desc="Asynchronous work accepted.")

# ---------------------------------------------------------------- accounts
model("UserPreferences", {"ghosting_days": "int?", "digest_local_time": "str?", "analytics_opt_out": "bool?",
                          "telegram_show_pay": "bool?", "followup_days": "[int]?"})
model("Me", {"id": "uuid", "email": "email", "email_verified": "bool", "display_name": "str?", "role": "Role",
             "status": "UserStatus", "locale": "str", "timezone": "str", "comparison_currency": "cur",
             "preferences": "UserPreferences", "mfa_enabled": "bool", "plan_code": "str?", "created_at": "dt"})
req("MeUpdate", {"display_name": "str?", "locale": "str?", "timezone": "str?", "comparison_currency": "cur?",
                 "preferences": "UserPreferences?"})
req("SignupRequest", {"email": "email", "password": "str", "invite_code": "str?", "locale": "str?",
                      "timezone": "str?", "accepted_terms_version": "str", "accepted_privacy_version": "str"})
req("LoginRequest", {"email": "email", "password": "str"})
model("LoginResponse", {"requires_totp": "bool", "user": "Me?"})
req("GoogleAuthRequest", {"code": "str", "state": "str", "code_verifier": "str"})
req("TotpVerifyRequest", {"code": "str"})
model("TotpEnrollResponse", {"otpauth_uri": "str", "secret": "str", "expires_at": "dt"},
      desc="Secret is shown once during enrolment only.")
req("TotpConfirmRequest", {"code": "str"})
req("VerifyEmailRequest", {"code": "str"})
req("PasswordResetRequest", {"email": "email"})
req("PasswordResetComplete", {"code": "str", "new_password": "str"})
model("PairStartResponse", {"code": "str", "expires_at": "dt"})
req("PairExchangeRequest", {"code": "str", "browser": "Browser", "client_version": "str"})
model("PairExchangeResponse", {"token": "str", "expires_at": "dt", "scopes": "[str]", "hosts": "[str]"},
      desc="Token is returned once; the extension stores it in browser storage.")
model("ClientToken", {"id": "uuid", "kind": "TokenKind", "label": "str?", "scopes": "[str]", "hosts": "[str]?",
                      "expires_at": "dt", "last_used_at": "dt?", "revoked_at": "dt?", "created_at": "dt"})
req("ClientTokenCreate", {"kind": "enum:runner|admin_api", "label": "str", "scopes": "[str]?"})
model("ClientTokenCreated", {"token": "str", "client_token": "ClientToken"}, desc="Secret shown once.")
req("SupportGrantCreate", {"granted_to": "uuid", "scope": "[str]", "reason": "str", "expires_at": "dt"})
model("SupportGrant", {"id": "uuid", "granted_to": "uuid", "scope": "[str]", "reason": "str", "expires_at": "dt",
                       "revoked_at": "dt?", "created_at": "dt"})

# ---------------------------------------------------------------- controls, usage, plans
model("LaneStatus", {"lane": "Lane", "enabled": "bool", "live_submit": "bool", "applied_today": "int", "daily_cap": "int?"})
model("StatusSummary", {"paused": "bool", "global_paused": "bool", "lanes": "[LaneStatus]", "applied_today": "int",
                        "open_questions": "int", "followups_due": "int", "interviews_today": "int",
                        "restriction": "MessageRef?"})
req("PauseRequest", {"scope": "enum:user|global?", "reason": "str?"})
req("FlagUpdate", {"value": "obj"}, desc="`value` is the flag's JSON value (boolean for toggles).")
model("Flag", {"key": "str", "scope": "enum:global|user", "value": "obj", "updated_at": "dt", "updated_by": "uuid?"})
model("UsageMeter", {"metric": "str", "used": "int", "limit": "int?", "period": "enum:day|month|rolling_30d",
                     "resets_at": "dt"})
model("Usage", {"plan_code": "str", "meters": "[UsageMeter]", "degraded": "enum:none|rules_only|budget"})
req("DryRunReviewRequest", {"attempt_ids": "[uuid]", "confirmed": "bool"})
model("DryRunReview", {"reviewed_at": "dt", "attempt_ids": "[uuid]", "live_submit_unlocked": "bool"})
model("PlanLimits", {"limits": "{int}", "documents_premium_model_allowed": "bool"},
      desc="Metric → limit, using canonical quota metric keys.")
model("Plan", {"code": "str", "name_key": "str", "limits": "PlanLimits", "active": "bool"})

# ---------------------------------------------------------------- packs, legal
model("MarketPackSummary", {"code": "str", "name": "str", "currency": "cur", "locales": "[str]", "rtl": "bool",
                            "cv_format": "str", "last_verified": "date?"})
model("RolePackSummary", {"code": "str", "field": "str?", "family": "str?", "title_aliases": "[str]",
                          "signal_documents": "[str]"})
model("PersonaPackSummary", {"code": "str", "description": "str", "daily_volume_range": "[int]"})
model("LegalDocument", {"doc": "LegalDoc", "version": "str", "locale": "str", "content_markdown": "str",
                        "effective_from": "date"})

# ---------------------------------------------------------------- profile
model("Location", {"country": "cc", "city": "str?", "remote_ok": "bool"})
model("Skill", {"name": "str", "years": "num?", "evidence": "str?"})
model("Credential", {"code": "str", "market": "str?", "valid_until": "date?"},
      desc="Credential numbers are never returned by the API.")
model("LanguageSkill", {"code": "str", "level": "str?"})
model("SalaryExpectation", {"currency": "cur", "min": "dec?", "max": "dec?", "period": "SalaryPeriod",
                            "basis": "SalaryBasis"})
model("Profile", {"id": "uuid", "version": "int", "persona": "str", "seniority": "Seniority", "years_exp": "num?",
                  "field_code": "str?", "role_family_code": "str?", "target_markets": "[str]", "target_roles": "[str]",
                  "locations": "[Location]", "skills": "[Skill]", "credentials": "[Credential]",
                  "salary_expectations": "[SalaryExpectation]", "notice_period_days": "int?",
                  "earliest_join_date": "date?", "visa_status": "{str}", "languages": "[LanguageSkill]",
                  "nationality": "str?", "excluded_keywords": "[str]", "india_tax_regime": "enum:new|old",
                  "min_fit_score": "int", "sensitive_fields_supplied": "[enum:photo|date_of_birth|marital_status]",
                  "updated_at": "dt"},
      desc="visa_status is keyed by ISO 3166-1 alpha-2 country code.")
req("ProfilePatch", {"persona": "str?", "seniority": "Seniority?", "years_exp": "num?", "target_markets": "[str]?",
                     "target_roles": "[str]?", "locations": "[Location]?", "skills": "[Skill]?",
                     "credentials": "[Credential]?", "salary_expectations": "[SalaryExpectation]?",
                     "notice_period_days": "int?", "earliest_join_date": "date?", "visa_status": "{str}?",
                     "languages": "[LanguageSkill]?", "nationality": "str?", "excluded_keywords": "[str]?",
                     "india_tax_regime": "enum:new|old?", "min_fit_score": "int?"})
model("ResumeDraftAccepted", {"draft_id": "uuid", "status": "enum:parsing|ready|failed"})
req("ResumeDraftApply", {"draft_id": "uuid", "fields": "[str]"},
    desc="Field paths from the draft the user confirmed.")
model("OnboardingStatus", {"persona": "str?", "steps": "[OnboardingStep]", "completed": "bool"})
model("OnboardingStep", {"code": "str", "done": "bool", "title": "MessageRef"})
model("FieldToggles", {"photo": "bool", "date_of_birth": "bool", "marital_status": "bool", "nationality": "bool",
                       "current_location": "bool", "visa_status": "bool", "notice_period": "bool"})
model("CvItem", {"section": "str", "text": "str", "source_ref": "str"},
      desc="Every CV item maps to a profile fact via source_ref.")
model("CvContent", {"items": "[CvItem]"})
model("ResumeVariant", {"id": "uuid", "name": "str", "market_format": "str", "role_code": "str?", "locale": "str",
                        "structured_content": "CvContent", "field_toggles_default": "FieldToggles",
                        "created_at": "dt", "updated_at": "dt"})
req("ResumeVariantCreate", {"name": "str", "market_format": "str", "role_code": "str?", "locale": "str"})
req("ResumeVariantPatch", {"name": "str?", "structured_content": "CvContent?", "field_toggles_default": "FieldToggles?"})
model("Answer", {"id": "uuid", "question_canonical": "str", "question_variants": "[str]", "answer": "str",
                 "scope": "AnswerScope", "scope_value": "str?", "last_used_at": "dt?", "created_at": "dt"})
req("AnswerCreate", {"question_canonical": "str", "question_variants": "[str]?", "answer": "str",
                     "scope": "AnswerScope", "scope_value": "str?"})
req("AnswerPatch", {"question_variants": "[str]?", "answer": "str?", "scope": "AnswerScope?", "scope_value": "str?"})

# ---------------------------------------------------------------- consents, inboxes, companies
model("Consent", {"id": "uuid", "source": "ConsentSource", "purpose": "str", "scope": "[str]",
                  "text_version": "str", "granted_at": "dt", "revoked_at": "dt?"})
req("ConsentGrant", {"source": "ConsentSource", "text_version": "str", "scope": "[str]?"})
req("GmailConnectRequest", {"redirect_uri": "url"})
model("GmailConnectResponse", {"authorization_url": "url", "state": "str"})
model("Inbox", {"id": "uuid", "kind": "InboxKind", "status": "InboxStatus", "sender_allowlist": "[str]",
                "forwarding_address": "email?", "pending_confirmation": "MessageRef?", "last_synced_at": "dt?",
                "consent_id": "uuid"})
model("CompanySuggestion", {"id": "uuid", "company_name": "str", "apply_host": "str", "detected_ats": "str?",
                            "detected_slug": "str?", "evidence_count": "int", "status": "SuggestionStatus",
                            "created_at": "dt"})
req("SuggestionDecision", {"decision": "enum:accept|reject", "ats_slug": "str?"})
model("InboundMailAccepted", {"accepted": "bool"})

# ---------------------------------------------------------------- matching, jobs
model("Deduction", {"label": "MessageRef", "amount": "dec"})
model("Assumption", {"key": "str", "params": "obj?"})
model("CompBreakdown", {"market": "str", "annual_gross": "dec?", "monthly_gross": "dec?", "deductions": "[Deduction]",
                        "in_hand_monthly": "dec?", "comparison_currency": "cur", "in_hand_monthly_comparison": "dec?",
                        "assumptions": "[Assumption]", "stale_fx": "bool", "not_disclosed": "[str]"},
      desc="Pay comparison from the market's CompensationModel; undisclosed parts are listed, never estimated.")
model("EligibilityReason", {"code": "str", "params": "obj?", "severity": "enum:block|warn|info"})
model("ScoreBreakdown", {"fit": "int?", "freshness": "num", "company_quality": "num", "strategy_weight": "num",
                         "rank_score": "num"})
model("JobCard", {"job_id": "uuid", "title": "str", "company": "str", "country": "cc?", "city": "str?",
                  "remote_type": "RemoteType?", "posted_at": "dt?", "apply_host": "str?", "lane": "Lane"})
model("RankedJob", {"job": "JobCard", "tier": "int", "eligible": "bool", "reasons": "[EligibilityReason]",
                    "similarity": "num?", "fit_score": "int?", "matched_skills": "[str]", "missing_skills": "[str]",
                    "missing_credentials": "[str]", "rationale": "untrusted?", "why": "MessageRef",
                    "pay": "CompBreakdown?", "application_id": "uuid?", "breakdown": "ScoreBreakdown"})
model("Salary", {"min": "dec?", "max": "dec?", "currency": "cur", "period": "SalaryPeriod", "basis": "SalaryBasis"})
model("JobDetail", {"job": "JobCard", "description": "untrusted", "url": "url", "apply_url": "url?",
                    "seniority": "Seniority?", "employment_type": "EmploymentType?", "allowed_regions": "[str]",
                    "salary": "Salary?", "visa_sponsorship": "VisaSponsorship", "visa_confidence": "num?",
                    "residency_required": "bool?", "languages_required": "[str]", "credentials_required": "[str]",
                    "ghost_score": "int?", "scam_score": "int?", "access_modes": "[AccessMode]",
                    "score": "RankedJob?", "application_id": "uuid?", "first_seen_at": "dt", "last_seen_at": "dt"})
model("Explanation", {"job_id": "uuid", "eligible": "bool", "reasons": "[EligibilityReason]",
                      "breakdown": "ScoreBreakdown?", "matched_skills": "[str]", "missing_skills": "[str]",
                      "missing_credentials": "[str]", "rationale": "untrusted?", "model": "str?",
                      "prompt_version": "str?"})
req("FeedbackRequest", {"rating": "int", "reason_code": "str?"})
model("Feedback", {"job_id": "uuid", "rating": "int", "reason_code": "str?", "created_at": "dt"})
req("JobApplyRequest", {"lane": "Lane?", "resume_variant_id": "uuid?", "field_toggles": "FieldToggles?"})
model("ApplicationView", {"id": "uuid", "job_id": "uuid", "company_id": "uuid?", "job": "JobCard?",
                          "state": "ApplicationState", "state_reason": "StateReason?", "lane": "Lane", "saved": "bool",
                          "applied_via": "AppliedVia?", "applied_at": "dt?", "last_event_at": "dt"})
model("JobActionResult", {"application": "ApplicationView", "undo": "UndoInfo?"})

# ---------------------------------------------------------------- applications, questions, documents
model("EventDetail", {"reason": "str?", "email_id": "uuid?", "attempt_id": "uuid?", "round": "int?",
                      "revived": "bool?", "undo_of": "uuid?"})
model("ApplicationEvent", {"id": "uuid", "from_state": "ApplicationState?", "to_state": "ApplicationState",
                           "trigger": "Trigger", "detail": "EventDetail", "created_at": "dt"})
req("TransitionRequest", {"to_state": "ApplicationState", "expected_from": "ApplicationState?", "reason": "str?"})
model("TransitionResult", {"application": "ApplicationView", "event_id": "uuid", "undo": "UndoInfo?"})
req("UndoRequest", {"undo_token": "str"})
req("QueueRequest", {"lane": "Lane", "resume_variant_id": "uuid?", "field_toggles": "FieldToggles?"})
model("AttemptView", {"id": "uuid", "adapter": "str", "mode": "AttemptMode", "status": "AttemptStatus",
                      "error_code": "str?", "screenshot": "SignedFileRef?", "payload": "SignedFileRef?",
                      "started_at": "dt", "finished_at": "dt?"})
model("PreparedAnswer", {"question": "str", "answer": "str", "answer_bank_id": "uuid"})
model("RenderedDocument", {"document_render_id": "uuid", "docx": "SignedFileRef?", "pdf": "SignedFileRef?"})
model("OneTapPack", {"document_render_id": "uuid", "cv": "RenderedDocument", "cover_note": "str",
                     "answers": "[PreparedAnswer]", "unanswered_questions": "[str]", "apply_url": "url"})
req("ConfirmAppliedRequest", {"applied_at": "dt?", "note": "str?"})
model("Question", {"id": "uuid", "application_id": "uuid", "question_text": "untrusted", "field_type": "FieldType",
                   "options": "[str]?", "status": "enum:open|answered|dismissed", "created_at": "dt"})
req("AnswerQuestionRequest", {"answer": "str?", "dismiss": "bool?", "save_to_bank": "bool?",
                              "scope": "AnswerScope?", "scope_value": "str?"})
req("DocumentRenderRequest", {"resume_variant_id": "uuid", "job_id": "uuid?", "kind": "DocumentKind",
                              "locale": "str?", "field_toggles": "FieldToggles?", "tailor": "bool?"})
model("ClaimCheckResult", {"passed": "bool", "unmapped_claims": "[str]"})
model("DocumentRender", {"id": "uuid", "resume_variant_id": "uuid", "job_id": "uuid?", "kind": "DocumentKind",
                         "locale": "str", "field_toggles": "FieldToggles", "claim_check": "ClaimCheckResult",
                         "docx": "SignedFileRef?", "pdf": "SignedFileRef?", "model": "str?",
                         "prompt_version": "str?", "created_at": "dt"})

# ---------------------------------------------------------------- lifecycle extras
req("EmailLinkRequest", {"application_id": "uuid?", "not_job_related": "bool?"})
model("EmailView", {"id": "uuid", "from_domain": "str", "subject": "untrusted", "received_at": "dt",
                    "classification": "EmailClassification", "application_id": "uuid?", "link_confidence": "num?"})
model("Contact", {"id": "uuid", "company_id": "uuid?", "name": "str", "role": "str?", "linkedin_url": "url?",
                  "email": "email?", "relation": "ContactRelation", "notes": "str?", "source": "enum:user|email"})
req("ContactCreate", {"company_id": "uuid?", "name": "str", "role": "str?", "linkedin_url": "url?", "email": "email?",
                      "relation": "ContactRelation", "notes": "str?"})
req("ContactPatch", {"company_id": "uuid?", "name": "str?", "role": "str?", "linkedin_url": "url?", "email": "email?",
                     "relation": "ContactRelation?", "notes": "str?"})
model("StoryRef", {"source_ref": "str", "summary": "str"})
model("PrepPack", {"assessment_types": "[str]", "likely_topics": "[str]", "user_stories": "[StoryRef]",
                   "company_notes": "[untrusted]", "prompt_version": "str?"})
model("Interview", {"id": "uuid", "application_id": "uuid", "round": "int", "type": "InterviewType",
                    "scheduled_at": "dt?", "meeting_url": "url?", "prep_pack": "PrepPack?",
                    "outcome": "InterviewOutcome?", "notes": "str?"})
req("InterviewCreate", {"application_id": "uuid", "round": "int", "type": "InterviewType", "scheduled_at": "dt?",
                        "meeting_url": "url?", "notes": "str?"})
model("Offer", {"id": "uuid", "application_id": "uuid", "currency": "cur", "period": "enum:month|year",
                "base": "dec?", "variable": "dec?", "joining_bonus": "dec?", "allowances_total": "dec?",
                "allowances": "{str}?", "equity": "obj?", "ctc": "dec?", "in_hand_monthly_est": "dec?",
                "comparison": "CompBreakdown?", "joining_date": "date?", "deadline": "date?"})
req("OfferCreate", {"application_id": "uuid", "currency": "cur", "period": "enum:month|year", "base": "dec?",
                    "variable": "dec?", "joining_bonus": "dec?", "allowances": "{str}?", "equity": "obj?",
                    "ctc": "dec?", "joining_date": "date?", "deadline": "date?"})
req("OfferPatch", {"base": "dec?", "variable": "dec?", "joining_bonus": "dec?", "allowances": "{str}?",
                   "equity": "obj?", "ctc": "dec?", "joining_date": "date?", "deadline": "date?"})
model("OfferComparison", {"currency": "cur", "fx_as_of": "date", "rows": "[CompBreakdown]"})

# ---------------------------------------------------------------- notify
model("DigestItem", {"job_id": "uuid", "application_id": "uuid?", "title": "str", "company": "str", "market": "str",
                     "fit_score": "int?", "why": "MessageRef", "pay": "CompBreakdown?"})
model("Digest", {"local_date": "date", "items": "[DigestItem]", "empty_reason_key": "str?",
                 "pending_questions": "int", "followups_due": "int", "interviews_today": "int"})
model("ActionSpec", {"label_key": "str", "action": "str", "target_id": "uuid", "value": "str?"})
model("Notification", {"id": "uuid", "event": "NotificationEvent", "message": "MessageRef", "deep_link": "str",
                       "actions": "[ActionSpec]", "created_at": "dt", "read_at": "dt?"})
req("MarkReadRequest", {"ids": "[uuid]?", "all": "bool?"})
model("QuietHours", {"start": "str", "end": "str"})
model("EventPreference", {"event": "NotificationEvent", "channels": "[Channel]"})
model("NotificationPrefs", {"events": "[EventPreference]", "quiet_hours": "QuietHours?"})
req("NotificationPrefsUpdate", {"events": "[EventPreference]", "quiet_hours": "QuietHours?"})
req("PushSubscriptionCreate", {"endpoint": "url", "keys": "{str}", "user_agent": "str?"})
model("PushSubscription", {"id": "uuid", "user_agent": "str?", "created_at": "dt"})
model("TelegramLinkCode", {"code": "str", "expires_at": "dt", "deep_link": "url"})
req("TelegramLinkRequest", {"code": "str", "chat_id": "str"})
model("TelegramLinkResponse", {"token": "str", "scopes": "[str]", "user_locale": "str"},
      desc="Per-user Telegram client token; the bot stores it encrypted, keyed by chat ID.")
req("ActionRequest", {"token": "str", "value": "str?"})
model("ActionResult", {"action": "str", "target_id": "uuid", "result": "MessageRef", "deep_link": "str?"})

# ---------------------------------------------------------------- strategy, insights
model("SourcePlan", {"channel": "str", "weight": "num"})
model("LanePlan", {"lane": "Lane", "enabled": "bool", "daily_cap": "int"})
model("SearchPlan", {"version": "int", "markets": "[str]", "market_weights": "{num}", "roles": "[str]",
                     "role_weights": "{num}", "sources": "[SourcePlan]", "lanes": "[LanePlan]",
                     "daily_application_target": "[int]", "min_fit_score": "int", "llm_top_n": "int",
                     "digest_max_items": "int", "tailoring_depth": "enum:light|standard|deep",
                     "explanations": "[MessageRef]"})
model("PlanDiffItem", {"path": "str", "old": "obj?", "new": "obj?", "reason": "MessageRef"})
model("PlanProposal", {"version": "int", "status": "PlanStatus", "plan": "SearchPlan", "diff": "[PlanDiffItem]",
                       "created_at": "dt"})
model("DateRange", {"from": "date", "to": "date"})
model("WeekValue", {"iso_week": "str", "value": "num"})
model("RateStat", {"numerator": "int", "denominator": "int", "rate": "num?", "ci_low": "num?", "ci_high": "num?"})
model("DimensionStat", {"dimension": "str", "applications": "int", "callbacks": "int", "interviews": "int",
                        "callback_rate": "RateStat"})
model("InsightsSummary", {"range": "DateRange", "interviews_per_week": "[WeekValue]",
                          "applications_per_week": "[WeekValue]", "callback_rate": "RateStat",
                          "ghosting_rate": "RateStat", "median_days_to_first_response": "num?",
                          "by_source": "[DimensionStat]", "by_market": "[DimensionStat]",
                          "by_variant": "[DimensionStat]", "by_lane": "[DimensionStat]"})
model("FunnelStage", {"state": "enum:matched|queued|applied|acknowledged|assessment|interview|offer", "count": "int",
                      "conversion_from_previous": "num?"})
model("Funnel", {"range": "DateRange", "stages": "[FunnelStage]", "dimension": "str?"})
model("ChartPoint", {"x": "str", "y": "num?", "series": "str"})
model("ChartSeries", {"chart": "ChartName", "range": "DateRange", "unit": "str", "points": "[ChartPoint]",
                      "series_labels": "{str}"},
      desc="Series are identified by stable keys; the client maps them to chart colour tokens.")
model("WeeklyReport", {"iso_week": "str", "interviews": "int", "interviews_change": "int", "applications": "int",
                       "callback_rate": "RateStat", "highlights": "[MessageRef]", "recommendations": "[MessageRef]",
                       "plan_proposal_version": "int?"})
req("ProductEvent", {"name": "str", "properties": "obj?", "occurred_at": "dt"})
req("ProductEventBatch", {"events": "[ProductEvent]"})

# ---------------------------------------------------------------- privacy
model("ExportJob", {"id": "uuid", "status": "ExportStatus", "requested_at": "dt", "completed_at": "dt?",
                    "expires_at": "dt?"})
req("DeletionRequest", {"password": "str?", "totp_code": "str?", "confirm": "bool"},
    desc="Re-authentication: password (or a fresh Google sign-in) and TOTP when enabled.")
model("DeletionJob", {"status": "DeletionStatus", "requested_at": "dt", "scheduled_for": "dt"})

# ---------------------------------------------------------------- extension
model("ExtStatus", {"paired": "bool", "user_locale": "str", "paused": "bool", "assist_hosts": "[str]",
                    "one_tap_hosts": "[str]", "min_client_version": "str", "flags": "{bool}"})
model("ExtQueueItem", {"application_id": "uuid", "job": "JobCard", "lane": "Lane", "state": "ApplicationState",
                       "state_reason": "StateReason?"})
req("PageContextRequest", {"url": "url"}, desc="URL only; page content is never sent.")
model("PageContext", {"host": "str", "access_modes": "[AccessMode]", "job_id": "uuid?", "application_id": "uuid?",
                      "match": "RankedJob?"})
req("AssistPlanRequest", {"url": "url", "application_id": "uuid?"})
model("SelectorHint", {"label": "str?", "name": "str?", "ats_field_id": "str?"})
model("AssistField", {"selector_hint": "SelectorHint", "field_type": "FieldType", "value": "obj?",
                      "source": "enum:profile|answer_bank|document|unknown", "question_text": "untrusted?"})
model("GuardSummary", {"allowed": "bool", "reasons": "[MessageRef]"})
model("AssistPlan", {"application_id": "uuid", "host": "str", "adapter": "str", "fields": "[AssistField]",
                     "files": "[SignedFileRef]", "guards": "GuardSummary", "plan_version": "str"},
      desc="Never contains a submit instruction; the user always clicks submit.")
req("SaveJobRequest", {"url": "url", "title": "str"})
model("SavedJob", {"job_id": "uuid?", "application_id": "uuid", "matched_existing": "bool"})
S["ExtensionProofUpload"] = {
    "type": "object", "additionalProperties": False, "required": ["screenshot", "proof"],
    "properties": {"screenshot": {"type": "string", "contentMediaType": "image/png"},
                   "proof": ref("ExtensionProofMeta")}}
req("ExtensionProofMeta", {"submitted_values": "obj", "plan_version": "str", "client_version": "str"})
model("ProofRecorded", {"application": "ApplicationView", "attempt_id": "uuid"})

# ---------------------------------------------------------------- runner
req("RunnerRegister", {"name": "str", "version": "str"})
model("Runner", {"id": "uuid", "name": "str", "version": "str", "status": "enum:online|offline|revoked",
                 "last_heartbeat_at": "dt?"})
req("RunnerHeartbeat", {"version": "str", "busy_task_id": "uuid?", "submitting_attempt_id": "uuid?"})
model("HeartbeatAck", {"server_time": "dt", "paused": "bool", "min_client_version": "str"})
req("LeaseRequest", {"wait_seconds": "int?", "kinds": "[RunnerTaskKind]?"})
model("DelayProfile", {"min_action_ms": "int", "max_action_ms": "int", "typing_cps_min": "num", "typing_cps_max": "num"})
model("RunnerTaskPayload", {"application_id": "uuid", "attempt_id": "uuid", "host": "str", "apply_url": "url",
                            "form_plan": "obj", "files": "[SignedFileRef]", "mode": "enum:dry_run|live",
                            "delays": "DelayProfile", "min_client_version": "str"})
model("Lease", {"task_id": "uuid", "kind": "RunnerTaskKind", "lease_expires_at": "dt", "payload": "RunnerTaskPayload"})
model("UnknownQuestion", {"field_id": "str", "question_text": "untrusted", "field_type": "FieldType",
                          "options": "[str]?"})
req("RunnerResult", {"outcome": "enum:submitted|dry_run_done|failed|needs_review|aborted", "error_code": "str?",
                     "unknown_questions": "[UnknownQuestion]?", "screenshot_file_id": "uuid?",
                     "payload_file_id": "uuid?"})
model("RunnerResultAck", {"task_id": "uuid", "status": "RunnerTaskStatus"})
S["RunnerUpload"] = {"type": "object", "additionalProperties": False, "required": ["file", "kind", "task_id"],
                     "properties": {"file": {"type": "string", "contentMediaType": "application/octet-stream"},
                                    "kind": {"type": "string", "enum": ["screenshot", "payload_snapshot"]},
                                    "task_id": {"type": "string", "format": "uuid"}}}
model("UploadRef", {"file_id": "uuid"})

# ---------------------------------------------------------------- admin
model("ConnectorStatus", {"connector": "str", "enabled": "bool", "status": "SourceRunStatus",
                          "last_run_at": "dt?", "last_success_at": "dt?", "jobs_found_7d": "int",
                          "jobs_new_7d": "int", "error_rate_7d": "num", "degraded_reason": "str?"})
model("CompanyCheck", {"company_id": "uuid", "name": "str", "ats": "str?",
                       "result": "enum:valid|not_found|no_target_postings|error"})
model("VerifyCompaniesResult", {"checked": "int", "results": "[CompanyCheck]"})
model("QueueStats", {"queue": "str", "depth": "int", "oldest_task_age_s": "num", "p95_latency_s": "num?",
                     "workers": "int"})
model("DeadLetter", {"id": "uuid", "task_name": "str", "task_args": "obj", "user_id": "uuid?", "error_type": "str",
                     "error_message": "str", "attempts": "int", "status": "DeadLetterStatus", "created_at": "dt",
                     "resolved_at": "dt?"})
model("RolloutChecklistItem", {"code": "str", "done": "bool", "evidence": "str?"})
model("RolloutStatus", {"kind": "enum:market|role", "code": "str", "enabled": "bool", "conformance_green": "bool",
                        "checklist": "[RolloutChecklistItem]", "blocked_by": "[enum:rollout_incomplete|conformance_failing]"})
model("LlmUsage", {"range": "DateRange", "tokens_total": "int", "cost_usd": "dec", "cost_per_mau_usd": "dec?",
                   "mau": "int", "tier2_coverage": "RateStat", "by_task": "{int}", "by_model_tier": "{int}",
                   "cache_hit_rate": "num?"})
model("AuditEntry", {"id": "uuid", "actor_user_id": "uuid?", "subject_user_id": "uuid?", "action": "str",
                     "target_type": "str?", "target_id": "uuid?", "detail": "obj", "correlation_id": "uuid?",
                     "created_at": "dt"})
model("AdminUserRow", {"id": "uuid", "email": "email", "role": "Role", "status": "UserStatus", "plan_code": "str?",
                       "created_at": "dt"}, desc="Directory data only; never profile or application content.")
req("RoleUpdate", {"role": "Role", "reason": "str"})
req("PlanAssignment", {"plan_code": "str", "overrides": "{int}?", "reason": "str"})
model("UserPlan", {"user_id": "uuid", "plan_code": "str", "overrides": "{int}?", "started_at": "dt"})
model("UserContent", {"grant_id": "uuid", "scope": "[str]", "profile": "Profile?",
                      "applications": "[ApplicationView]?", "expires_at": "dt"},
      desc="Returned only under an active support grant; limited to the granted scope; every read is audited.")
model("AbuseSignal", {"id": "uuid", "user_id": "uuid", "kind": "AbuseKind", "severity": "int", "detail": "obj",
                      "created_at": "dt", "reviewed_at": "dt?"})
req("AbuseReview", {"decision": "enum:dismiss|cooldown|suspend", "days": "int?", "reason_key": "str"})
model("Restriction", {"id": "uuid", "kind": "RestrictionKind", "reason_key": "str", "starts_at": "dt", "ends_at": "dt?"})
model("AbuseReviewResult", {"signal": "AbuseSignal", "restriction": "Restriction?"})
req("InviteCreate", {"email": "email?", "plan_code": "str", "expires_at": "dt"})
model("InviteCreated", {"id": "uuid", "code": "str", "expires_at": "dt"}, desc="Invite code shown once.")

# ---------------------------------------------------------------- operation details
# (method, path) -> dict(op=operationId, req=schema|None, res=(status, schema|None), q=[query params], mp=multipart)
P = "Page:"
D = {
    ("GET", "/health"): dict(op="core_get_health", res=(200, "HealthStatus")),
    ("GET", "/ready"): dict(op="core_get_readiness", res=(200, "ReadinessStatus")),
    ("POST", "/auth/signup"): dict(op="accounts_create_signup", req="SignupRequest", res=(201, "Me")),
    ("POST", "/auth/login"): dict(op="accounts_create_login", req="LoginRequest", res=(200, "LoginResponse")),
    ("POST", "/auth/google"): dict(op="accounts_create_google_login", req="GoogleAuthRequest", res=(200, "LoginResponse")),
    ("POST", "/auth/totp"): dict(op="accounts_verify_totp", req="TotpVerifyRequest", res=(200, "Me")),
    ("POST", "/auth/totp/enroll"): dict(op="accounts_start_totp_enrolment", res=(200, "TotpEnrollResponse")),
    ("POST", "/auth/totp/confirm"): dict(op="accounts_confirm_totp_enrolment", req="TotpConfirmRequest", res=(204, None)),
    ("POST", "/auth/logout"): dict(op="accounts_delete_session", res=(204, None)),
    ("POST", "/auth/logout-everywhere"): dict(op="accounts_delete_all_sessions", res=(204, None)),
    ("POST", "/auth/verify-email"): dict(op="accounts_verify_email", req="VerifyEmailRequest", res=(204, None)),
    ("POST", "/auth/password-reset/request"): dict(op="accounts_request_password_reset", req="PasswordResetRequest", res=(202, None)),
    ("POST", "/auth/password-reset/complete"): dict(op="accounts_complete_password_reset", req="PasswordResetComplete", res=(204, None)),
    ("POST", "/auth/pair/start"): dict(op="accounts_start_extension_pairing", res=(201, "PairStartResponse")),
    ("POST", "/auth/pair/exchange"): dict(op="accounts_exchange_pairing_code", req="PairExchangeRequest", res=(201, "PairExchangeResponse")),
    ("GET", "/me"): dict(op="accounts_get_me", res=(200, "Me")),
    ("PATCH", "/me"): dict(op="accounts_update_me", req="MeUpdate", res=(200, "Me")),
    ("GET", "/tokens"): dict(op="accounts_list_tokens", res=(200, P + "ClientToken"), q=["limit", "cursor"]),
    ("POST", "/tokens"): dict(op="accounts_create_token", req="ClientTokenCreate", res=(201, "ClientTokenCreated")),
    ("DELETE", "/tokens/{token_id}"): dict(op="accounts_revoke_token", res=(204, None)),
    ("POST", "/support-grants"): dict(op="accounts_create_support_grant", req="SupportGrantCreate", res=(201, "SupportGrant")),
    ("DELETE", "/support-grants/{grant_id}"): dict(op="accounts_revoke_support_grant", res=(204, None)),
    ("GET", "/me/status"): dict(op="controls_get_status", res=(200, "StatusSummary")),
    ("POST", "/control/pause"): dict(op="controls_create_pause", req="PauseRequest", res=(200, "StatusSummary")),
    ("POST", "/control/resume"): dict(op="controls_create_resume", req="PauseRequest", res=(200, "StatusSummary")),
    ("PATCH", "/flags/{key}"): dict(op="controls_update_user_flag", req="FlagUpdate", res=(200, "Flag")),
    ("GET", "/me/usage"): dict(op="quotas_get_usage", res=(200, "Usage")),
    ("POST", "/me/dry-run-review"): dict(op="apply_create_dry_run_review", req="DryRunReviewRequest", res=(201, "DryRunReview")),
    ("GET", "/plans"): dict(op="quotas_list_plans", res=(200, P + "Plan"), q=["limit", "cursor"]),
    ("GET", "/packs/markets"): dict(op="packs_list_markets", res=(200, P + "MarketPackSummary"), q=["limit", "cursor"]),
    ("GET", "/packs/roles"): dict(op="packs_list_roles", res=(200, P + "RolePackSummary"), q=["q", "limit", "cursor"]),
    ("GET", "/packs/personas"): dict(op="packs_list_personas", res=(200, P + "PersonaPackSummary"), q=["limit", "cursor"]),
    ("GET", "/legal/{doc}"): dict(op="privacy_get_legal_document", res=(200, "LegalDocument"), q=["version", "locale"]),
    ("GET", "/profile"): dict(op="profile_get_profile", res=(200, "Profile"), etag=True),
    ("PATCH", "/profile"): dict(op="profile_update_profile", req="ProfilePatch", res=(200, "Profile"), etag=True, if_match=True),
    ("POST", "/profile/resume"): dict(op="profile_create_resume_draft", mp="ResumeUpload", res=(202, "ResumeDraftAccepted")),
    ("POST", "/profile/resume/apply"): dict(op="profile_apply_resume_draft", req="ResumeDraftApply", res=(200, "Profile")),
    ("GET", "/onboarding/status"): dict(op="profile_get_onboarding_status", res=(200, "OnboardingStatus")),
    ("GET", "/resume-variants"): dict(op="profile_list_resume_variants", res=(200, P + "ResumeVariant"), q=["limit", "cursor"]),
    ("POST", "/resume-variants"): dict(op="profile_create_resume_variant", req="ResumeVariantCreate", res=(201, "ResumeVariant")),
    ("PATCH", "/resume-variants/{variant_id}"): dict(op="profile_update_resume_variant", req="ResumeVariantPatch", res=(200, "ResumeVariant"), etag=True, if_match=True),
    ("GET", "/answers"): dict(op="profile_list_answers", res=(200, P + "Answer"), q=["q", "answer_scope", "limit", "cursor"]),
    ("POST", "/answers"): dict(op="profile_create_answer", req="AnswerCreate", res=(201, "Answer")),
    ("PATCH", "/answers/{answer_id}"): dict(op="profile_update_answer", req="AnswerPatch", res=(200, "Answer"), etag=True, if_match=True),
    ("DELETE", "/answers/{answer_id}"): dict(op="profile_delete_answer", res=(204, None)),
    ("GET", "/consents"): dict(op="privacy_list_consents", res=(200, P + "Consent"), q=["limit", "cursor"]),
    ("POST", "/consents"): dict(op="privacy_create_consent", req="ConsentGrant", res=(201, "Consent")),
    ("DELETE", "/consents/{source}"): dict(op="privacy_revoke_consent", res=(204, None)),
    ("POST", "/inboxes/gmail/connect"): dict(op="connectors_create_gmail_connection", req="GmailConnectRequest", res=(200, "GmailConnectResponse"), consent=True),
    ("POST", "/inboxes/forwarding"): dict(op="connectors_create_forwarding_inbox", res=(201, "Inbox"), consent=True),
    ("GET", "/inboxes"): dict(op="connectors_list_inboxes", res=(200, P + "Inbox"), q=["limit", "cursor"]),
    ("DELETE", "/inboxes/{inbox_id}"): dict(op="connectors_delete_inbox", res=(204, None)),
    ("GET", "/companies/suggestions"): dict(op="connectors_list_company_suggestions", res=(200, P + "CompanySuggestion"), q=["suggestion_status", "limit", "cursor"]),
    ("POST", "/companies/suggestions/{suggestion_id}/decision"): dict(op="connectors_create_suggestion_decision", req="SuggestionDecision", res=(200, "CompanySuggestion")),
    ("POST", "/inbound/mail"): dict(op="connectors_create_inbound_mail", mp="InboundMail", res=(202, "InboundMailAccepted")),
    ("GET", "/matches"): dict(op="matching_list_matches", res=(200, P + "RankedJob"), q=["market", "min_fit", "q", "since", "sort", "limit", "cursor"]),
    ("GET", "/matches/possible"): dict(op="matching_list_possible_matches", res=(200, P + "RankedJob"), q=["market", "limit", "cursor"]),
    ("GET", "/jobs/{job_id}"): dict(op="matching_get_job", res=(200, "JobDetail")),
    ("GET", "/jobs/{job_id}/explain"): dict(op="matching_get_job_explanation", res=(200, "Explanation")),
    ("POST", "/jobs/{job_id}/score"): dict(op="matching_create_job_score", res=(200, "RankedJob"), upstream=True, quota=True),
    ("PUT", "/jobs/{job_id}/feedback"): dict(op="matching_put_job_feedback", req="FeedbackRequest", res=(200, "Feedback")),
    ("POST", "/jobs/{job_id}/apply"): dict(op="lifecycle_create_job_apply", req="JobApplyRequest", res=(200, "JobActionResult"), conflict=True, quota=True),
    ("POST", "/jobs/{job_id}/skip"): dict(op="lifecycle_create_job_skip", res=(200, "JobActionResult"), conflict=True),
    ("POST", "/jobs/{job_id}/save"): dict(op="lifecycle_create_job_save", res=(200, "JobActionResult"), conflict=True),
    ("GET", "/applications"): dict(op="lifecycle_list_applications", res=(200, P + "ApplicationView"), q=["state", "lane", "saved", "q", "sort", "limit", "cursor"]),
    ("GET", "/applications/{application_id}"): dict(op="lifecycle_get_application", res=(200, "ApplicationView"), etag=True),
    ("GET", "/applications/{application_id}/history"): dict(op="lifecycle_list_application_events", res=(200, P + "ApplicationEvent"), q=["limit", "cursor"]),
    ("POST", "/applications/{application_id}/transition"): dict(op="lifecycle_create_transition", req="TransitionRequest", res=(200, "TransitionResult"), conflict=True),
    ("POST", "/events/{event_id}/undo"): dict(op="lifecycle_create_undo", req="UndoRequest", res=(200, "ApplicationView"), conflict=True),
    ("POST", "/applications/{application_id}/queue"): dict(op="apply_create_queue", req="QueueRequest", res=(202, "ApplicationView"), conflict=True, quota=True),
    ("POST", "/applications/{application_id}/dry-run"): dict(op="apply_create_dry_run", res=(202, "AttemptView"), conflict=True),
    ("GET", "/applications/{application_id}/attempts"): dict(op="apply_list_attempts", res=(200, P + "AttemptView"), q=["limit", "cursor"]),
    ("GET", "/applications/{application_id}/one-tap-pack"): dict(op="apply_get_one_tap_pack", res=(200, "OneTapPack")),
    ("POST", "/applications/{application_id}/confirm-applied"): dict(op="apply_create_manual_confirmation", req="ConfirmAppliedRequest", res=(200, "ApplicationView"), conflict=True),
    ("GET", "/questions"): dict(op="apply_list_questions", res=(200, P + "Question"), q=["limit", "cursor"]),
    ("POST", "/questions/{question_id}/answer"): dict(op="apply_create_question_answer", req="AnswerQuestionRequest", res=(200, "Question"), conflict=True),
    ("POST", "/documents/render"): dict(op="documents_create_render", req="DocumentRenderRequest", res=(201, "DocumentRender"), upstream=True, quota=True),
    ("GET", "/documents/{render_id}"): dict(op="documents_get_render", res=(200, "DocumentRender")),
    ("GET", "/files/{file_id}/download"): dict(op="core_get_file_download", res=(302, None)),
    ("POST", "/emails/{email_id}/link"): dict(op="lifecycle_create_email_link", req="EmailLinkRequest", res=(200, "EmailView")),
    ("GET", "/contacts"): dict(op="lifecycle_list_contacts", res=(200, P + "Contact"), q=["company_id", "relation", "limit", "cursor"]),
    ("POST", "/contacts"): dict(op="lifecycle_create_contact", req="ContactCreate", res=(201, "Contact")),
    ("PATCH", "/contacts/{contact_id}"): dict(op="lifecycle_update_contact", req="ContactPatch", res=(200, "Contact"), etag=True, if_match=True),
    ("GET", "/interviews"): dict(op="lifecycle_list_interviews", res=(200, P + "Interview"), q=["upcoming", "limit", "cursor"]),
    ("POST", "/interviews"): dict(op="lifecycle_create_interview", req="InterviewCreate", res=(201, "Interview")),
    ("POST", "/interviews/{interview_id}/prep-pack"): dict(op="lifecycle_create_prep_pack", res=(200, "Interview"), upstream=True, quota=True),
    ("GET", "/offers"): dict(op="lifecycle_list_offers", res=(200, P + "Offer"), q=["limit", "cursor"]),
    ("POST", "/offers"): dict(op="lifecycle_create_offer", req="OfferCreate", res=(201, "Offer")),
    ("PATCH", "/offers/{offer_id}"): dict(op="lifecycle_update_offer", req="OfferPatch", res=(200, "Offer"), etag=True, if_match=True),
    ("GET", "/offers/compare"): dict(op="lifecycle_get_offer_comparison", res=(200, "OfferComparison"), q=["offer_id", "currency"]),
    ("GET", "/digest/today"): dict(op="notify_get_today_digest", res=(200, "Digest")),
    ("GET", "/notifications"): dict(op="notify_list_notifications", res=(200, P + "Notification"), q=["unread", "limit", "cursor"]),
    ("POST", "/notifications/read"): dict(op="notify_create_read_marks", req="MarkReadRequest", res=(204, None)),
    ("GET", "/notification-prefs"): dict(op="notify_get_preferences", res=(200, "NotificationPrefs")),
    ("PUT", "/notification-prefs"): dict(op="notify_put_preferences", req="NotificationPrefsUpdate", res=(200, "NotificationPrefs")),
    ("POST", "/push/subscriptions"): dict(op="notify_create_push_subscription", req="PushSubscriptionCreate", res=(201, "PushSubscription"), consent=True),
    ("DELETE", "/push/subscriptions/{subscription_id}"): dict(op="notify_delete_push_subscription", res=(204, None)),
    ("POST", "/notify/telegram/link-code"): dict(op="notify_create_telegram_link_code", res=(201, "TelegramLinkCode")),
    ("POST", "/notify/telegram/link"): dict(op="notify_create_telegram_link", req="TelegramLinkRequest", res=(201, "TelegramLinkResponse")),
    ("DELETE", "/notify/telegram/link"): dict(op="notify_delete_telegram_link", res=(204, None)),
    ("POST", "/actions"): dict(op="notify_create_action", req="ActionRequest", res=(200, "ActionResult"), conflict=True),
    ("GET", "/plan"): dict(op="strategy_get_plan", res=(200, "SearchPlan")),
    ("GET", "/plan/proposals"): dict(op="strategy_list_plan_proposals", res=(200, P + "PlanProposal"), q=["limit", "cursor"]),
    ("POST", "/plan/{version}/approve"): dict(op="strategy_create_plan_approval", res=(200, "PlanProposal"), conflict=True),
    ("POST", "/plan/{version}/reject"): dict(op="strategy_create_plan_rejection", res=(200, "PlanProposal"), conflict=True),
    ("GET", "/insights/summary"): dict(op="insights_get_summary", res=(200, "InsightsSummary"), q=["from", "to"]),
    ("GET", "/insights/funnel"): dict(op="insights_get_funnel", res=(200, "Funnel"), q=["from", "to", "dimension"]),
    ("GET", "/insights/charts/{chart}"): dict(op="insights_get_chart", res=(200, "ChartSeries"), q=["from", "to"]),
    ("GET", "/insights/weekly/{iso_week}"): dict(op="insights_get_weekly_report", res=(200, "WeeklyReport")),
    ("POST", "/events"): dict(op="insights_create_product_events", req="ProductEventBatch", res=(202, None)),
    ("POST", "/me/export"): dict(op="privacy_create_export", res=(202, "ExportJob")),
    ("GET", "/me/export/{export_id}"): dict(op="privacy_get_export", res=(200, "ExportJob")),
    ("GET", "/me/export/{export_id}/download"): dict(op="privacy_get_export_download", res=(302, None)),
    ("POST", "/me/delete"): dict(op="privacy_create_deletion", req="DeletionRequest", res=(202, "DeletionJob")),
    ("POST", "/me/delete/cancel"): dict(op="privacy_cancel_deletion", res=(204, None), conflict=True),
    ("GET", "/ext/status"): dict(op="extension_get_status", res=(200, "ExtStatus")),
    ("GET", "/ext/queue"): dict(op="extension_list_queue", res=(200, P + "ExtQueueItem"), q=["limit", "cursor"]),
    ("POST", "/ext/page-context"): dict(op="extension_create_page_context", req="PageContextRequest", res=(200, "PageContext")),
    ("POST", "/ext/assist-plan"): dict(op="extension_create_assist_plan", req="AssistPlanRequest", res=(200, "AssistPlan"), conflict=True),
    ("POST", "/ext/applications/{application_id}/proof"): dict(op="extension_create_proof", mp="ExtensionProofUpload", res=(201, "ProofRecorded"), conflict=True, quota=True),
    ("POST", "/ext/applications/{application_id}/confirm-applied"): dict(op="extension_create_manual_confirmation", req="ConfirmAppliedRequest", res=(200, "ApplicationView"), conflict=True),
    ("GET", "/ext/applications/{application_id}/one-tap-pack"): dict(op="extension_get_one_tap_pack", res=(200, "OneTapPack")),
    ("POST", "/ext/jobs/save"): dict(op="extension_create_saved_job", req="SaveJobRequest", res=(201, "SavedJob")),
    ("POST", "/runner/register"): dict(op="runner_create_registration", req="RunnerRegister", res=(201, "Runner")),
    ("POST", "/runner/heartbeat"): dict(op="runner_create_heartbeat", req="RunnerHeartbeat", res=(200, "HeartbeatAck")),
    ("POST", "/runner/tasks/lease"): dict(op="runner_create_lease", req="LeaseRequest", res=(200, "Lease"), no_content=True),
    ("POST", "/runner/tasks/{task_id}/result"): dict(op="runner_create_result", req="RunnerResult", res=(200, "RunnerResultAck"), conflict=True),
    ("POST", "/runner/uploads"): dict(op="runner_create_upload", mp="RunnerUpload", res=(201, "UploadRef")),
    ("GET", "/admin/connectors"): dict(op="admin_list_connectors", res=(200, P + "ConnectorStatus"), q=["limit", "cursor"]),
    ("POST", "/admin/companies/verify"): dict(op="admin_create_company_verification", res=(202, "VerifyCompaniesResult")),
    ("GET", "/admin/queues"): dict(op="admin_list_queues", res=(200, P + "QueueStats"), q=["limit", "cursor"]),
    ("GET", "/admin/dead-letters"): dict(op="admin_list_dead_letters", res=(200, P + "DeadLetter"), q=["dead_letter_status", "limit", "cursor"]),
    ("POST", "/admin/dead-letters/{dead_letter_id}/replay"): dict(op="admin_create_dead_letter_replay", res=(202, "DeadLetter"), conflict=True),
    ("POST", "/admin/dead-letters/{dead_letter_id}/discard"): dict(op="admin_create_dead_letter_discard", res=(200, "DeadLetter"), conflict=True),
    ("GET", "/admin/flags"): dict(op="admin_list_flags", res=(200, P + "Flag"), q=["limit", "cursor"]),
    ("PUT", "/admin/flags/{key}"): dict(op="admin_put_flag", req="FlagUpdate", res=(200, "Flag"), conflict=True),
    ("GET", "/admin/rollout"): dict(op="admin_list_rollout", res=(200, P + "RolloutStatus"), q=["limit", "cursor"]),
    ("GET", "/admin/llm-usage"): dict(op="admin_get_llm_usage", res=(200, "LlmUsage"), q=["from", "to"]),
    ("GET", "/admin/audit"): dict(op="admin_list_audit", res=(200, P + "AuditEntry"), q=["action", "subject_user_id", "from", "to", "limit", "cursor"]),
    ("GET", "/admin/users"): dict(op="admin_list_users", res=(200, P + "AdminUserRow"), q=["q", "limit", "cursor"]),
    ("PUT", "/admin/users/{user_id}/role"): dict(op="admin_put_user_role", req="RoleUpdate", res=(200, "AdminUserRow")),
    ("PUT", "/admin/users/{user_id}/plan"): dict(op="admin_put_user_plan", req="PlanAssignment", res=(200, "UserPlan")),
    ("GET", "/admin/users/{user_id}/content"): dict(op="admin_get_user_content", res=(200, "UserContent")),
    ("GET", "/admin/abuse"): dict(op="admin_list_abuse_signals", res=(200, P + "AbuseSignal"), q=["reviewed", "limit", "cursor"]),
    ("POST", "/admin/abuse/{signal_id}/review"): dict(op="admin_create_abuse_review", req="AbuseReview", res=(200, "AbuseReviewResult"), conflict=True),
    ("POST", "/admin/invites"): dict(op="admin_create_invite", req="InviteCreate", res=(201, "InviteCreated")),
}

model("HealthStatus", {"status": "enum:ok"})
model("ReadinessStatus", {"status": "enum:ok|degraded", "checks": "{str}"})
S["ResumeUpload"] = {"type": "object", "additionalProperties": False, "required": ["file"],
                     "properties": {"file": {"type": "string", "contentMediaType": "application/pdf",
                                             "description": "PDF or DOCX, ≤ 10 MB"}}}
S["InboundMail"] = {"type": "object", "additionalProperties": True,
                    "description": "Provider-specific inbound payload (raw MIME + envelope); provider chosen in Phase 11."}

IDEMPOTENT_REQUIRED = {
    ("POST", "/jobs/{job_id}/apply"), ("POST", "/applications/{application_id}/queue"),
    ("POST", "/applications/{application_id}/confirm-applied"),
    ("POST", "/ext/applications/{application_id}/confirm-applied"),
    ("POST", "/ext/applications/{application_id}/proof"),
    ("POST", "/runner/tasks/{task_id}/result"), ("POST", "/runner/uploads"),
    ("POST", "/me/export"), ("POST", "/me/delete"),
}
PUBLIC_NO_CLIENT_VERSION = {"/health", "/ready", "/inbound/mail", "/legal/{doc}", "/actions"}

QUERY = {
    "limit": {"name": "limit", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25}},
    "cursor": {"name": "cursor", "in": "query", "schema": {"type": "string"}, "description": "Opaque cursor from `next_cursor`."},
    "q": {"name": "q", "in": "query", "schema": {"type": "string", "maxLength": 200}, "description": "Instant search text."},
    "market": {"name": "market", "in": "query", "schema": {"type": "string"}, "description": "Market pack code."},
    "min_fit": {"name": "min_fit", "in": "query", "schema": {"type": "integer", "minimum": 0, "maximum": 100}},
    "since": {"name": "since", "in": "query", "schema": {"type": "string", "format": "date-time"}},
    "sort": {"name": "sort", "in": "query", "schema": {"type": "string"}, "description": "`field` or `-field` from the endpoint's allow-list."},
    "state": {"name": "state", "in": "query", "schema": {"type": "array", "items": ref("ApplicationState")}, "style": "form", "explode": True},
    "lane": {"name": "lane", "in": "query", "schema": ref("Lane")},
    "saved": {"name": "saved", "in": "query", "schema": {"type": "boolean"}},
    "answer_scope": {"name": "scope", "in": "query", "schema": ref("AnswerScope")},
    "suggestion_status": {"name": "status", "in": "query", "schema": ref("SuggestionStatus")},
    "dead_letter_status": {"name": "status", "in": "query", "schema": ref("DeadLetterStatus")},
    "company_id": {"name": "company_id", "in": "query", "schema": {"type": "string", "format": "uuid"}},
    "relation": {"name": "relation", "in": "query", "schema": ref("ContactRelation")},
    "upcoming": {"name": "upcoming", "in": "query", "schema": {"type": "boolean"}},
    "unread": {"name": "unread", "in": "query", "schema": {"type": "boolean"}},
    "offer_id": {"name": "offer_id", "in": "query", "required": True, "schema": {"type": "array", "items": {"type": "string", "format": "uuid"}, "minItems": 1}, "style": "form", "explode": True},
    "currency": {"name": "currency", "in": "query", "schema": {"type": "string", "pattern": "^[A-Z]{3}$"}},
    "from": {"name": "from", "in": "query", "schema": {"type": "string", "format": "date"}},
    "to": {"name": "to", "in": "query", "schema": {"type": "string", "format": "date"}},
    "dimension": {"name": "dimension", "in": "query", "schema": {"type": "string", "enum": ["source", "market", "variant", "lane"]}},
    "version": {"name": "version", "in": "query", "schema": {"type": "string"}},
    "locale": {"name": "locale", "in": "query", "schema": {"type": "string"}},
    "action": {"name": "action", "in": "query", "schema": {"type": "string"}},
    "subject_user_id": {"name": "subject_user_id", "in": "query", "schema": {"type": "string", "format": "uuid"}},
    "reviewed": {"name": "reviewed", "in": "query", "schema": {"type": "boolean"}},
}

PATH_PARAM_SCHEMAS = {
    "key": {"type": "string", "pattern": r"^[A-Za-z0-9_.<>|-]+$"},
    "source": ref("ConsentSource"),
    "doc": ref("LegalDoc"),
    "chart": ref("ChartName"),
    "iso_week": {"type": "string", "pattern": r"^\d{4}-W\d{2}$"},
    "version": {"type": "integer", "minimum": 1},
}

# ---------------------------------------------------------------- build
def parse_phase(text):
    m = re.match(r"(\d+)", text)
    return int(m.group(1))


def parse_stories(text):
    return re.findall(r"US-\d+\.\d+", text)


def parse_auth(text, method, path):
    """Return (security list, scopes, roles, notes)."""
    security, scopes, roles = [], [], None
    write = method != "GET"
    session = [{"session": [], "csrf": []}] if write else [{"session": []}]
    for m in re.finditer(r"([TERA]):`([^`]+)`", text):
        kind, scope = m.groups()
        scheme = {"T": "telegramToken", "E": "extensionToken", "R": "runnerToken", "A": "adminApiToken"}[kind]
        security.append({scheme: [scope]})
        scopes.append(scope)
    head = [p.strip() for p in re.sub(r"[TERA]:`[^`]+`", "", text).split(",")]
    for part in head:
        if not part:
            continue
        if part.startswith("S+MFA"):
            security[:0] = session
            roles = ["owner"] if "(owner)" in part else ["admin", "owner"]
        elif part.startswith("S"):
            security[:0] = session
        elif part == "K":
            security.append({"actionToken": []})
        elif part == "W":
            security.append({"webhookSignature": []})
        elif part.startswith("P"):
            security.append({})
        elif part.startswith("Bot service credential"):
            security.append({"botServiceToken": []})
    if text.startswith("P") and not security:
        security = [{}]
    return security, scopes, roles


def problem(code):
    return {"$ref": f"#/components/responses/{code}"}


paths = {}
operation_ids = set()
for o in ops:
    key = (o["method"], o["path"])
    d = D[key]
    tag = TAG_NAMES[o["tag"]]
    security, scopes, roles = parse_auth(o["auth"], o["method"], o["path"])
    op = {
        "operationId": d["op"],
        "summary": re.sub(r"`", "", o["purpose"]),
        "tags": [tag],
        "x-phase": parse_phase(o["phase"]),
        "x-story": parse_stories(o["story"]),
        "x-scopes": scopes,
    }
    if roles:
        op["x-roles"] = roles
    if key == ("GET", "/admin/users/{user_id}/content"):
        op["x-support-grant"] = "required"
    if key in IDEMPOTENT_REQUIRED:
        op["x-idempotency"] = "required"
    assert d["op"] not in operation_ids, d["op"]
    operation_ids.add(d["op"])
    op["security"] = security

    params = []
    for name in re.findall(r"\{(\w+)\}", o["path"]):
        params.append({"name": name, "in": "path", "required": True,
                       "schema": PATH_PARAM_SCHEMAS.get(name, {"type": "string", "format": "uuid"})})
    for qn in d.get("q", []):
        params.append(QUERY[qn])
    if o["path"] not in PUBLIC_NO_CLIENT_VERSION:
        params.append({"$ref": "#/components/parameters/ClientVersion"})
    params.append({"$ref": "#/components/parameters/CorrelationId"})
    if o["method"] == "POST" and o["path"] not in {"/health", "/ready"}:
        if key in IDEMPOTENT_REQUIRED:
            params.append({"$ref": "#/components/parameters/IdempotencyKeyRequired"})
        elif not o["path"].startswith("/auth/"):
            params.append({"$ref": "#/components/parameters/IdempotencyKey"})
    if d.get("if_match"):
        params.append({"$ref": "#/components/parameters/IfMatch"})
    op["parameters"] = params

    if d.get("req"):
        op["requestBody"] = {"required": True, "content": {"application/json": {"schema": ref(d["req"])}}}
    if d.get("mp"):
        op["requestBody"] = {"required": True, "content": {"multipart/form-data": {"schema": ref(d["mp"])}}}
        if d["mp"] == "InboundMail":
            op["requestBody"]["content"] = {"application/json": {"schema": ref("InboundMail")}}

    status, schema = d["res"]
    headers = {"X-Correlation-ID": {"$ref": "#/components/headers/X-Correlation-ID"}}
    if o["path"] not in {"/health", "/ready"}:
        headers.update({h: {"$ref": f"#/components/headers/{h}"} for h in ("RateLimit-Limit", "RateLimit-Remaining", "RateLimit-Reset")})
    if d.get("etag"):
        headers["ETag"] = {"$ref": "#/components/headers/ETag"}
    responses = {}
    if status == 302:
        responses["302"] = {"description": "Redirect to a short-lived signed URL.",
                            "headers": {**headers, "Location": {"schema": {"type": "string", "format": "uri"}}}}
    elif schema is None:
        responses[str(status)] = {"description": {204: "No content.", 202: "Accepted."}.get(status, "OK"), "headers": headers}
    else:
        if schema.startswith(P):
            item = schema[len(P):]
            page_name = item + "Page"
            S[page_name] = {"allOf": [ref("CursorPage"), {"type": "object", "properties": {"items": {"type": "array", "items": ref(item)}}}]}
            schema = page_name
        responses[str(status)] = {"description": "Success.", "headers": headers,
                                  "content": {"application/json": {"schema": ref(schema)}}}
    if d.get("no_content"):
        responses["204"] = {"description": "No task available within the wait time.", "headers": headers}

    public = security == [{}] or o["path"] in {"/health", "/ready"}
    if o["path"] not in {"/health", "/ready"}:
        responses["400"] = problem("BadRequest")
        if not public:
            responses["401"] = problem("Unauthenticated")
            responses["403"] = problem("Forbidden")
        if re.search(r"\{", o["path"]):
            responses["404"] = problem("NotFound")
        if d.get("conflict"):
            responses["409"] = problem("Conflict")
        if d.get("if_match"):
            responses["412"] = problem("PreconditionFailed")
        if op.get("requestBody") or d.get("q") or re.search(r"\{", o["path"]):
            responses["422"] = problem("ValidationFailed")
        if o["path"] not in PUBLIC_NO_CLIENT_VERSION:
            responses["426"] = problem("ClientOutdated")
        if d.get("consent"):
            responses["428"] = problem("ConsentRequired")
        responses["429"] = problem("TooManyRequests")
        if d.get("upstream"):
            responses["502"] = problem("UpstreamError")
            responses["503"] = problem("Unavailable")
    else:
        responses["503"] = {"description": "Not ready.", "content": {"application/json": {"schema": ref("ReadinessStatus")}}} if o["path"] == "/ready" else None
        responses = {k: v for k, v in responses.items() if v}
    responses["500"] = problem("InternalError")
    op["responses"] = responses

    path_item = paths.setdefault(o["path"], {})
    if o["path"] in {"/health", "/ready"}:
        path_item["servers"] = [{"url": "/", "description": "Unversioned probe endpoints"}]
    path_item[o["method"].lower()] = op


def problem_response(desc, extra_headers=None):
    r = {"description": desc, "headers": {"X-Correlation-ID": {"$ref": "#/components/headers/X-Correlation-ID"}},
         "content": {"application/problem+json": {"schema": ref("Problem")}}}
    if extra_headers:
        r["headers"].update(extra_headers)
    return r


retry = {"Retry-After": {"$ref": "#/components/headers/Retry-After"}}
components = {
    "securitySchemes": {
        "session": {"type": "apiKey", "in": "cookie", "name": "jr_session",
                    "description": "Server-side web session (HttpOnly, Secure, SameSite=Lax). Admin/owner sessions must be MFA-verified for admin operations."},
        "csrf": {"type": "apiKey", "in": "header", "name": "X-CSRF-Token",
                 "description": "Double-submit token equal to the `jr_csrf` cookie; required with `session` on every state-changing request."},
        "extensionToken": {"type": "http", "scheme": "bearer", "bearerFormat": "jr_extension_*",
                           "description": "Scoped, host-limited, rotating token from extension pairing."},
        "telegramToken": {"type": "http", "scheme": "bearer", "bearerFormat": "jr_telegram_*",
                          "description": "Per-user token issued at Telegram linking; held encrypted by the bot."},
        "runnerToken": {"type": "http", "scheme": "bearer", "bearerFormat": "jr_runner_*"},
        "adminApiToken": {"type": "http", "scheme": "bearer", "bearerFormat": "jr_admin_api_*"},
        "botServiceToken": {"type": "http", "scheme": "bearer", "bearerFormat": "jr_bot_*",
                            "description": "Bot service credential; only valid for exchanging a Telegram link code."},
        "actionToken": {"type": "apiKey", "in": "header", "name": "X-Action-Token",
                        "description": "Signed, single-purpose action token from a notification button (72 h, single use where not idempotent). Sent as a header so it never lands in server or proxy logs; `/actions` also accepts it in the JSON body for email links opened via the web app."},
        "webhookSignature": {"type": "apiKey", "in": "header", "name": "X-Webhook-Signature",
                             "description": "HMAC signature from the inbound mail provider."},
    },
    "parameters": {
        "ClientVersion": {"name": "X-Client-Version", "in": "header", "required": True,
                          "schema": {"type": "string", "pattern": r"^[a-z_]+@\d+\.\d+\.\d+"},
                          "description": "`<app>@<semver>`; below the minimum the API returns 426."},
        "CorrelationId": {"name": "X-Correlation-ID", "in": "header", "required": False,
                          "schema": {"type": "string", "format": "uuid"}},
        "IdempotencyKey": {"name": "Idempotency-Key", "in": "header", "required": False,
                           "schema": {"type": "string", "format": "uuid"},
                           "description": "First response stored 24 h per (user, key, route) and replayed."},
        "IdempotencyKeyRequired": {"name": "Idempotency-Key", "in": "header", "required": True,
                                   "schema": {"type": "string", "format": "uuid"}},
        "IfMatch": {"name": "If-Match", "in": "header", "required": True, "schema": {"type": "string"},
                    "description": "ETag from the last GET; mismatch returns 412."},
        "Limit": QUERY["limit"],
        "Cursor": QUERY["cursor"],
    },
    "headers": {
        "X-Correlation-ID": {"schema": {"type": "string", "format": "uuid"}},
        "ETag": {"schema": {"type": "string"}},
        "RateLimit-Limit": {"schema": {"type": "integer"}},
        "RateLimit-Remaining": {"schema": {"type": "integer"}},
        "RateLimit-Reset": {"schema": {"type": "integer"}, "description": "Seconds until the window resets."},
        "Retry-After": {"schema": {"type": "integer"}},
    },
    "responses": {
        "BadRequest": problem_response("Malformed request or unknown parameter (`bad_request`)."),
        "Unauthenticated": problem_response("Missing or expired credentials (`unauthenticated`)."),
        "Forbidden": problem_response("Missing scope or role, CSRF failure or MFA required (`forbidden`, `csrf_failed`, `mfa_required`)."),
        "NotFound": problem_response("Not found, including resources owned by another user (`not_found`)."),
        "Conflict": problem_response("Conflict (`conflict`, `invalid_transition`, `concurrency_conflict`, `guard_failed`)."),
        "PreconditionFailed": problem_response("ETag mismatch (`precondition_failed`)."),
        "ValidationFailed": problem_response("Validation failed (`validation_failed`); see `errors[]`."),
        "ClientOutdated": problem_response("Client version below minimum (`client_outdated`)."),
        "ConsentRequired": problem_response("Consent for the source is required first (`consent_required`)."),
        "TooManyRequests": problem_response("Rate limit, quota or LLM budget exceeded (`rate_limited`, `quota_exceeded`, `budget_exceeded`).", retry),
        "UpstreamError": problem_response("External service failed (`upstream_error`)."),
        "Unavailable": problem_response("Temporarily unavailable (`upstream_unavailable`, `paused`).", retry),
        "InternalError": problem_response("Unexpected error (`internal_error`); body carries only the correlation ID."),
    },
    "schemas": dict(sorted(S.items())),
}

tag_desc = {
    "health": "Liveness and readiness probes (unversioned).",
    "accounts": "Sign-in, sessions, MFA, client tokens and support grants.",
    "controls": "Pause/resume, user flags, status, usage and plans.",
    "packs": "Read-only market/role/persona packs and legal documents.",
    "profile": "Profile, resume drafts, CV variants, answer bank and onboarding.",
    "inboxes": "Consents, alert inboxes and company suggestions.",
    "matching": "Matches, job detail, explanations, scoring and job actions.",
    "applications": "Applications pipeline, questions, attempts and documents.",
    "lifecycle": "Email linking, contacts, interviews and offers.",
    "notify": "Digest, notifications, preferences and channels.",
    "insights": "Search plan, proposals, insights and product events.",
    "privacy": "Export and account deletion.",
    "extension": "Browser extension endpoints.",
    "runner": "Optional home runner endpoints.",
    "admin": "Admin console (operational data only).",
}

spec = {
    "openapi": "3.1.0",
    "info": {
        "title": "JobRadar API",
        "version": "0.1.0",
        "description": "Contract for all v1 operations. Human-readable rules (auth, errors, pagination, idempotency, "
                       "rate limits) are in docs/api.md. Vendor extensions: x-phase (first phase that ships the "
                       "operation), x-story (PRD stories), x-scopes (client-token scopes), x-roles, x-idempotency, "
                       "x-support-grant, x-untrusted.",
    },
    "servers": [{"url": "/api/v1"}],
    "tags": [{"name": k, "description": v} for k, v in tag_desc.items()],
    "paths": paths,
    "components": components,
}


class Dumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


out = ROOT / "docs" / "openapi.yaml"
header = "# Generated contract for JobRadar API v1. Source of truth for endpoints: docs/api.md §9.\n"
out.write_text(header + yaml.dump(spec, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")
print(f"operations={sum(len([k for k in v if k != 'servers']) for v in paths.values())} catalogue={len(ops)}")
