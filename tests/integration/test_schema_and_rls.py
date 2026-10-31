"""Phase 2 schema: migrations, model/schema drift, row-level security and constraints."""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import jobradar.models  # noqa: F401 -- registers tables
from alembic import command
from jobradar.core.base import Base
from jobradar.core.db import system_session, user_session
from jobradar.core.ids import new_id
from jobradar.core.scope import ClientKind, Role, UserScope, system_scope

pytestmark = [pytest.mark.integration, pytest.mark.anyio]
NOW = datetime(2026, 10, 30, 8, 0, tzinfo=UTC)
# Tables with a user_id column that are deliberately not under RLS (operational, IDs only).
RLS_EXEMPT = {"dead_letters"}


def scope_for(user_id: UUID) -> UserScope:
    return UserScope(user_id=user_id, roles=frozenset({Role.USER}), via=ClientKind.WEB)


@pytest.fixture
def two_users(admin_engine: Engine) -> tuple[UUID, UUID]:
    alice, bob = new_id(), new_id()
    with admin_engine.begin() as connection:
        for user_id, email in ((alice, "alice@example.org"), (bob, "bob@example.org")):
            connection.execute(
                text("INSERT INTO users (id, email) VALUES (:id, :email)"),
                {"id": user_id, "email": email},
            )
            connection.execute(
                text(
                    "INSERT INTO consents (id, user_id, source, purpose, scope, text_version, "
                    "granted_at) VALUES (:id, :user_id, 'gmail_alerts', 'consent.gmail_alerts', "
                    "'{gmail.readonly}', 'v1', :now)"
                ),
                {"id": new_id(), "user_id": user_id, "now": NOW},
            )
    return alice, bob


def test_migrations_downgrade_and_upgrade_cleanly(
    admin_engine: Engine, migrated_url: str, make_alembic_config: Callable[[str], Config]
) -> None:
    with admin_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("DROP DATABASE IF EXISTS migration_cycle"))
        connection.execute(text("CREATE DATABASE migration_cycle"))
    cycle_url = migrated_url.rsplit("/", 1)[0] + "/migration_cycle"
    config = make_alembic_config(cycle_url)

    command.upgrade(config, "head")
    command.downgrade(config, "0001_phase0")
    command.upgrade(config, "head")

    engine = create_engine(cycle_url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == (
            "0002_phase2"
        )
    engine.dispose()


def test_models_match_the_migrated_schema(admin_engine: Engine) -> None:
    with admin_engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        differences = compare_metadata(context, Base.metadata)

    assert differences == []


def test_every_user_owned_table_has_forced_row_level_security(admin_engine: Engine) -> None:
    with admin_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity FROM pg_class c "
                "JOIN information_schema.columns col ON col.table_name = c.relname "
                "WHERE col.column_name = 'user_id' AND col.table_schema = 'public' "
                "AND c.relkind = 'r'"
            )
        ).all()

    unprotected = [name for name, rls, forced in rows if not (rls and forced)]
    assert set(unprotected) == RLS_EXEMPT


async def test_user_sees_only_own_rows(
    two_users: tuple[UUID, UUID], session_factory: async_sessionmaker[AsyncSession]
) -> None:
    alice, _ = two_users

    async with user_session(scope_for(alice), factory=session_factory) as session:
        consent_users = (await session.execute(text("SELECT user_id FROM consents"))).scalars()
        visible_users = (await session.execute(text("SELECT id FROM users"))).scalars()

        assert set(consent_users) == {alice}
        assert set(visible_users) == {alice}


async def test_user_cannot_write_rows_for_another_user(
    two_users: tuple[UUID, UUID], session_factory: async_sessionmaker[AsyncSession]
) -> None:
    alice, bob = two_users

    with pytest.raises(DBAPIError, match="row-level security"):
        async with user_session(scope_for(alice), factory=session_factory) as session:
            await session.execute(
                text(
                    "INSERT INTO consents (id, user_id, source, purpose, scope, text_version, "
                    "granted_at) VALUES (:id, :bob, 'telegram', 'p', '{}', 'v1', now())"
                ),
                {"id": new_id(), "bob": bob},
            )


async def test_app_role_without_a_bound_user_sees_nothing(
    two_users: tuple[UUID, UUID], session_factory: async_sessionmaker[AsyncSession]
) -> None:
    async with session_factory() as session, session.begin():
        await session.execute(text('SET LOCAL ROLE "jobradar_app"'))
        count = (await session.execute(text("SELECT count(*) FROM consents"))).scalar()

    assert count == 0


async def test_corpus_role_writes_jobs_but_cannot_read_user_tables(
    two_users: tuple[UUID, UUID], session_factory: async_sessionmaker[AsyncSession]
) -> None:
    async with system_session(system_scope("discover_all"), factory=session_factory) as session:
        await session.execute(
            text(
                "INSERT INTO jobs (id, company_name_raw, title, url, content_hash, dedupe_hash, "
                "first_seen_at, last_seen_at) VALUES (:id, 'Example', 'Engineer', "
                "'https://example.org/1', '\\x01', '\\x02', now(), now())"
            ),
            {"id": new_id()},
        )

    with pytest.raises(DBAPIError, match="permission denied"):
        async with system_session(system_scope("x"), factory=session_factory) as session:
            await session.execute(text("SELECT count(*) FROM consents"))


async def test_flags_show_global_and_own_only(
    two_users: tuple[UUID, UUID],
    admin_engine: Engine,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    alice, bob = two_users
    with admin_engine.begin() as connection:
        for key, scope, user_id in (
            ("market.uae.enabled", "global", None),
            ("lane.auto.enabled", "user", alice),
            ("lane.auto.enabled", "user", bob),
        ):
            connection.execute(
                text(
                    "INSERT INTO settings_flags (id, key, scope, user_id, value) "
                    "VALUES (:id, :key, :scope, :user_id, 'true')"
                ),
                {"id": new_id(), "key": key, "scope": scope, "user_id": user_id},
            )

    async with user_session(scope_for(alice), factory=session_factory) as session:
        rows = (await session.execute(text("SELECT scope, user_id FROM settings_flags"))).all()

    assert sorted((scope, user_id) for scope, user_id in rows) == [
        ("global", None),
        ("user", alice),
    ]

    with pytest.raises(DBAPIError, match="row-level security"):
        async with user_session(scope_for(alice), factory=session_factory) as session:
            await session.execute(
                text(
                    "INSERT INTO settings_flags (id, key, scope, value) "
                    "VALUES (:id, 'PAUSE_ALL', 'global', 'true')"
                ),
                {"id": new_id()},
            )


async def test_source_runs_show_shared_and_own_runs(
    two_users: tuple[UUID, UUID],
    admin_engine: Engine,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    alice, bob = two_users
    with admin_engine.begin() as connection:
        for user_id in (None, alice, bob):
            connection.execute(
                text(
                    "INSERT INTO source_runs (id, connector, user_id, started_at) "
                    "VALUES (:id, 'gmail_alerts', :user_id, now())"
                ),
                {"id": new_id(), "user_id": user_id},
            )

    async with user_session(scope_for(alice), factory=session_factory) as session:
        owners = (await session.execute(text("SELECT user_id FROM source_runs"))).scalars()

    assert sorted(owners, key=str) == sorted([None, alice], key=str)


async def test_audit_log_is_append_only(
    two_users: tuple[UUID, UUID], session_factory: async_sessionmaker[AsyncSession]
) -> None:
    alice, _ = two_users
    async with user_session(scope_for(alice), factory=session_factory) as session:
        await session.execute(
            text(
                "INSERT INTO audit_log (id, subject_user_id, action) "
                "VALUES (:id, :alice, 'consent.granted')"
            ),
            {"id": new_id(), "alice": alice},
        )

    with pytest.raises(DBAPIError, match="permission denied"):
        async with user_session(scope_for(alice), factory=session_factory) as session:
            await session.execute(text("UPDATE audit_log SET action = 'x'"))


def test_job_dedupe_hash_is_unique(admin_engine: Engine) -> None:
    insert = text(
        "INSERT INTO jobs (id, company_name_raw, title, url, content_hash, dedupe_hash, "
        "first_seen_at, last_seen_at) VALUES (:id, 'Example', 'Engineer', 'https://x.org', "
        "'\\x01', '\\xaa', now(), now())"
    )
    with admin_engine.begin() as connection:
        connection.execute(insert, {"id": new_id()})

    with pytest.raises(IntegrityError), admin_engine.begin() as connection:
        connection.execute(insert, {"id": new_id()})


def test_company_name_without_domain_is_unique(admin_engine: Engine) -> None:
    insert = text(
        "INSERT INTO companies (id, name, normalized_name) VALUES (:id, 'Example', 'example')"
    )
    with admin_engine.begin() as connection:
        connection.execute(insert, {"id": new_id()})

    with pytest.raises(IntegrityError), admin_engine.begin() as connection:
        connection.execute(insert, {"id": new_id()})


def test_only_one_active_consent_per_source(
    two_users: tuple[UUID, UUID], admin_engine: Engine
) -> None:
    alice, _ = two_users

    with pytest.raises(IntegrityError), admin_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO consents (id, user_id, source, purpose, scope, text_version, "
                "granted_at) VALUES (:id, :alice, 'gmail_alerts', 'p', '{}', 'v2', now())"
            ),
            {"id": new_id(), "alice": alice},
        )
