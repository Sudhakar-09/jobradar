"""Phase 2 discovery tables, database roles and row-level security.

Creates only the tables Phase 2 uses (docs/lld/database.md §9). Row-level security
(database.md §4) is enforced through two login-less roles that every session switches into:

- ``jobradar_app``: all application tables; user-owned rows filtered by ``app.user_id``.
- ``jobradar_corpus``: shared tables only (companies, jobs, job_sources, system source runs).

Superusers bypass RLS, so sessions must ``SET LOCAL ROLE`` (core.db) and the migrating login is
granted membership in both roles. Roles are cluster-wide: the downgrade revokes their grants but
does not drop them.

Revision ID: 0002_phase2
Revises: 0001_phase0
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_phase2"
down_revision: str | None = "0001_phase0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "jobradar_app"
CORPUS_ROLE = "jobradar_corpus"
CURRENT_USER_ID = "app_current_user_id()"
TENANT_TABLES = ("consents", "company_suggestions", "alert_inboxes", "alert_messages")
SHARED_TABLES = ("companies", "jobs", "job_sources")


def _create_roles() -> None:
    for role in (APP_ROLE, CORPUS_ROLE):
        op.execute(
            f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{role}') "
            f"THEN CREATE ROLE {role} NOLOGIN; END IF; END $$"
        )
        op.execute(f"GRANT {role} TO CURRENT_USER")
        op.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
    op.execute(
        "CREATE FUNCTION app_current_user_id() RETURNS uuid LANGUAGE sql STABLE AS "
        "$$ SELECT NULLIF(current_setting('app.user_id', true), '')::uuid $$"
    )


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def _grant_and_protect() -> None:
    dml = "SELECT, INSERT, UPDATE, DELETE"
    for table in ("users", *TENANT_TABLES, *SHARED_TABLES, "source_runs", "settings_flags"):
        op.execute(f"GRANT {dml} ON {table} TO {APP_ROLE}")
    for table in (*SHARED_TABLES, "source_runs"):
        op.execute(f"GRANT {dml} ON {table} TO {CORPUS_ROLE}")
    op.execute(f"GRANT SELECT ON settings_flags TO {CORPUS_ROLE}")
    for table in ("audit_log", "dead_letters"):  # append-only for application roles
        op.execute(f"GRANT SELECT, INSERT ON {table} TO {APP_ROLE}, {CORPUS_ROLE}")

    _enable_rls("users")
    op.execute(
        f"CREATE POLICY self_only ON users TO {APP_ROLE} "
        f"USING (id = {CURRENT_USER_ID}) WITH CHECK (id = {CURRENT_USER_ID})"
    )
    for table in TENANT_TABLES:
        _enable_rls(table)
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} TO {APP_ROLE} "
            f"USING (user_id = {CURRENT_USER_ID}) WITH CHECK (user_id = {CURRENT_USER_ID})"
        )

    _enable_rls("source_runs")
    own_or_shared = f"user_id IS NULL OR user_id = {CURRENT_USER_ID}"
    op.execute(
        f"CREATE POLICY own_or_shared ON source_runs TO {APP_ROLE} "
        f"USING ({own_or_shared}) WITH CHECK ({own_or_shared})"
    )
    op.execute(
        f"CREATE POLICY shared_only ON source_runs TO {CORPUS_ROLE} "
        "USING (user_id IS NULL) WITH CHECK (user_id IS NULL)"
    )

    _enable_rls("settings_flags")
    own_user_flag = f"scope = 'user' AND user_id = {CURRENT_USER_ID}"
    op.execute(
        f"CREATE POLICY read_global_and_own ON settings_flags FOR SELECT TO {APP_ROLE} "
        f"USING (scope = 'global' OR user_id = {CURRENT_USER_ID})"
    )
    for command in ("INSERT", "UPDATE", "DELETE"):
        using = "" if command == "INSERT" else f" USING ({own_user_flag})"
        check = "" if command == "DELETE" else f" WITH CHECK ({own_user_flag})"
        op.execute(
            f"CREATE POLICY write_own_{command.lower()} ON settings_flags FOR {command} "
            f"TO {APP_ROLE}{using}{check}"
        )
    op.execute(
        f"CREATE POLICY read_global ON settings_flags FOR SELECT TO {CORPUS_ROLE} "
        "USING (scope = 'global')"
    )

    _enable_rls("audit_log")
    op.execute(
        f"CREATE POLICY read_own ON audit_log FOR SELECT TO {APP_ROLE} "
        f"USING (subject_user_id = {CURRENT_USER_ID})"
    )
    op.execute(
        f"CREATE POLICY append ON audit_log FOR INSERT TO {APP_ROLE}, {CORPUS_ROLE} "
        "WITH CHECK (true)"
    )


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    _create_roles()
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("subject_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=True),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column(
            "detail",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("correlation_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index(
        "ix_audit_log_action_created_at", "audit_log", ["action", "created_at"], unique=False
    )
    op.create_index(
        "ix_audit_log_subject_user_id_created_at",
        "audit_log",
        ["subject_user_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "companies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("normalized_name", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=True),
        sa.Column("ats", sa.Text(), nullable=True),
        sa.Column("ats_slug", sa.Text(), nullable=True),
        sa.Column(
            "countries", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False
        ),
        sa.Column(
            "sponsor_flags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("quality_score", sa.SmallInteger(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_not_found", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("status", sa.Text(), server_default="active", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "ats IS NULL OR ats IN ('greenhouse', 'lever', 'ashby', 'workable', 'smartrecruiters', 'workday', 'other')",
            name=op.f("ck_companies_ats"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'not_found', 'disabled')", name=op.f("ck_companies_status")
        ),
        sa.CheckConstraint(
            "quality_score IS NULL OR quality_score BETWEEN 0 AND 100",
            name=op.f("ck_companies_quality_score"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_companies")),
    )
    op.create_index(
        "ix_companies_countries", "companies", ["countries"], unique=False, postgresql_using="gin"
    )
    op.create_index(
        "uq_companies_ats_ats_slug",
        "companies",
        ["ats", "ats_slug"],
        unique=True,
        postgresql_where=sa.text("ats_slug IS NOT NULL"),
    )
    op.create_index(
        "uq_companies_normalized_name_domain",
        "companies",
        ["normalized_name", "domain"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )
    op.create_table(
        "dead_letters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_name", sa.Text(), nullable=False),
        sa.Column("task_args", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("error_type", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("attempts", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.Text(), server_default="open", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "status IN ('open', 'replayed', 'discarded')", name=op.f("ck_dead_letters_status")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dead_letters")),
    )
    op.create_index(
        "ix_dead_letters_status_created_at", "dead_letters", ["status", "created_at"], unique=False
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("role", sa.Text(), server_default="user", nullable=False),
        sa.Column("status", sa.Text(), server_default="active", nullable=False),
        sa.Column("locale", sa.Text(), server_default="en", nullable=False),
        sa.Column("timezone", sa.Text(), server_default="Asia/Kolkata", nullable=False),
        sa.Column("comparison_currency", sa.String(length=3), server_default="INR", nullable=False),
        sa.Column(
            "preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("role IN ('user', 'admin', 'owner')", name=op.f("ck_users_role")),
        sa.CheckConstraint(
            "status IN ('active', 'suspended', 'pending_deletion')", name=op.f("ck_users_status")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "company_suggestions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("apply_host", sa.Text(), nullable=False),
        sa.Column("detected_ats", sa.Text(), nullable=True),
        sa.Column("detected_slug", sa.Text(), nullable=True),
        sa.Column("evidence_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected')",
            name=op.f("ck_company_suggestions_status"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_company_suggestions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_company_suggestions")),
    )
    op.create_index(
        "ix_company_suggestions_user_id_status",
        "company_suggestions",
        ["user_id", "status"],
        unique=False,
    )
    op.create_table(
        "consents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("scope", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("text_version", sa.Text(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_consents_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consents")),
    )
    op.create_index("ix_consents_user_id_source", "consents", ["user_id", "source"], unique=False)
    op.create_index(
        "uq_consents_user_id_source_active",
        "consents",
        ["user_id", "source"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("company_name_raw", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("apply_url", sa.Text(), nullable=True),
        sa.Column("apply_host", sa.Text(), nullable=True),
        sa.Column("location_raw", sa.Text(), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.LargeBinary(), nullable=False),
        sa.Column("dedupe_hash", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.Text(), server_default="active", nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'expired', 'removed')", name=op.f("ck_jobs_status")
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_jobs_company_id_companies"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index("ix_jobs_apply_host", "jobs", ["apply_host"], unique=False)
    op.create_index(
        "ix_jobs_country_status_last_seen_at",
        "jobs",
        ["country", "status", "last_seen_at"],
        unique=False,
    )
    op.create_index("ix_jobs_first_seen_at", "jobs", ["first_seen_at"], unique=False)
    op.create_index("uq_jobs_dedupe_hash", "jobs", ["dedupe_hash"], unique=True)
    op.create_table(
        "settings_flags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(scope = 'global' AND user_id IS NULL) OR (scope = 'user' AND user_id IS NOT NULL)",
            name=op.f("ck_settings_flags_scope_user"),
        ),
        sa.CheckConstraint("scope IN ('global', 'user')", name=op.f("ck_settings_flags_scope")),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name=op.f("fk_settings_flags_updated_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_settings_flags_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_settings_flags")),
    )
    op.create_index(
        "uq_settings_flags_key_global",
        "settings_flags",
        ["key"],
        unique=True,
        postgresql_where=sa.text("scope = 'global'"),
    )
    op.create_index(
        "uq_settings_flags_key_user_id",
        "settings_flags",
        ["key", "user_id"],
        unique=True,
        postgresql_where=sa.text("scope = 'user'"),
    )
    op.create_table(
        "source_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("connector", sa.Text(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), server_default="running", nullable=False),
        sa.Column("jobs_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("jobs_new", sa.Integer(), server_default="0", nullable=False),
        sa.Column("jobs_updated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("items_invalid", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "http_status_counts",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'ok', 'partial', 'failed', 'degraded')",
            name=op.f("ck_source_runs_status"),
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_source_runs_company_id_companies"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_source_runs_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_runs")),
    )
    op.create_index(
        "ix_source_runs_company_id_started_at",
        "source_runs",
        ["company_id", "started_at"],
        unique=False,
        postgresql_where=sa.text("company_id IS NOT NULL"),
    )
    op.create_index(
        "ix_source_runs_connector_started_at",
        "source_runs",
        ["connector", "started_at"],
        unique=False,
    )
    op.create_table(
        "alert_inboxes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("oauth_token_enc", sa.LargeBinary(), nullable=True),
        sa.Column("sender_allowlist", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("status", sa.Text(), server_default="active", nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("kind IN ('gmail', 'forwarding')", name=op.f("ck_alert_inboxes_kind")),
        sa.CheckConstraint(
            "status IN ('active', 'reauth_required', 'revoked')",
            name=op.f("ck_alert_inboxes_status"),
        ),
        sa.ForeignKeyConstraint(
            ["consent_id"],
            ["consents.id"],
            name=op.f("fk_alert_inboxes_consent_id_consents"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_alert_inboxes_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alert_inboxes")),
    )
    op.create_index("ix_alert_inboxes_user_id", "alert_inboxes", ["user_id"], unique=False)
    op.create_table(
        "job_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_job_id", sa.Text(), nullable=False),
        sa.Column("source_run_id", sa.Uuid(), nullable=True),
        sa.Column(
            "raw",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_job_sources_job_id_jobs"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_run_id"],
            ["source_runs.id"],
            name=op.f("fk_job_sources_source_run_id_source_runs"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_sources")),
    )
    op.create_index("ix_job_sources_job_id", "job_sources", ["job_id"], unique=False)
    op.create_index(
        "uq_job_sources_source_source_job_id",
        "job_sources",
        ["source", "source_job_id"],
        unique=True,
    )
    op.create_table(
        "alert_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("inbox_id", sa.Uuid(), nullable=False),
        sa.Column("provider_message_id", sa.Text(), nullable=False),
        sa.Column("sender", sa.Text(), nullable=False),
        sa.Column("parser", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("jobs_parsed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('parsed', 'unparsed', 'ignored')", name=op.f("ck_alert_messages_status")
        ),
        sa.ForeignKeyConstraint(
            ["inbox_id"],
            ["alert_inboxes.id"],
            name=op.f("fk_alert_messages_inbox_id_alert_inboxes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_alert_messages_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alert_messages")),
    )
    op.create_index(
        "ix_alert_messages_user_id_received_at",
        "alert_messages",
        ["user_id", "received_at"],
        unique=False,
    )
    op.create_index(
        "uq_alert_messages_inbox_id_provider_message_id",
        "alert_messages",
        ["inbox_id", "provider_message_id"],
        unique=True,
    )
    _grant_and_protect()


def downgrade() -> None:
    for role in (APP_ROLE, CORPUS_ROLE):
        op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {role}")
        op.execute(f"REVOKE USAGE ON SCHEMA public FROM {role}")
    op.drop_index("uq_alert_messages_inbox_id_provider_message_id", table_name="alert_messages")
    op.drop_index("ix_alert_messages_user_id_received_at", table_name="alert_messages")
    op.drop_table("alert_messages")
    op.drop_index("uq_job_sources_source_source_job_id", table_name="job_sources")
    op.drop_index("ix_job_sources_job_id", table_name="job_sources")
    op.drop_table("job_sources")
    op.drop_index("ix_alert_inboxes_user_id", table_name="alert_inboxes")
    op.drop_table("alert_inboxes")
    op.drop_index("ix_source_runs_connector_started_at", table_name="source_runs")
    op.drop_index(
        "ix_source_runs_company_id_started_at",
        table_name="source_runs",
        postgresql_where=sa.text("company_id IS NOT NULL"),
    )
    op.drop_table("source_runs")
    op.drop_index(
        "uq_settings_flags_key_user_id",
        table_name="settings_flags",
        postgresql_where=sa.text("scope = 'user'"),
    )
    op.drop_index(
        "uq_settings_flags_key_global",
        table_name="settings_flags",
        postgresql_where=sa.text("scope = 'global'"),
    )
    op.drop_table("settings_flags")
    op.drop_index("uq_jobs_dedupe_hash", table_name="jobs")
    op.drop_index("ix_jobs_first_seen_at", table_name="jobs")
    op.drop_index("ix_jobs_country_status_last_seen_at", table_name="jobs")
    op.drop_index("ix_jobs_apply_host", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index(
        "uq_consents_user_id_source_active",
        table_name="consents",
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.drop_index("ix_consents_user_id_source", table_name="consents")
    op.drop_table("consents")
    op.drop_index("ix_company_suggestions_user_id_status", table_name="company_suggestions")
    op.drop_table("company_suggestions")
    op.drop_table("users")
    op.drop_index("ix_dead_letters_status_created_at", table_name="dead_letters")
    op.drop_table("dead_letters")
    op.drop_index("uq_companies_normalized_name_domain", table_name="companies")
    op.drop_index(
        "uq_companies_ats_ats_slug",
        table_name="companies",
        postgresql_where=sa.text("ats_slug IS NOT NULL"),
    )
    op.drop_index("ix_companies_countries", table_name="companies", postgresql_using="gin")
    op.drop_table("companies")
    op.drop_index("ix_audit_log_subject_user_id_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_action_created_at", table_name="audit_log")
    op.drop_table("audit_log")
    # ### end Alembic commands ###
    op.execute("DROP FUNCTION IF EXISTS app_current_user_id()")
