from datetime import datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.application.contact_deletion import ContactDeletionBatch
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaContactDataRow,
    WaContactEmailRow,
    WaContactRightRow,
    WaContactRow,
    WaUserGroupRow,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.repositories import (
    SQLAlchemyContactRepository,
)


_AUXILIARY_DDL = (
    """
    CREATE TABLE wa_verification_channel_assets (
        id INTEGER PRIMARY KEY,
        address TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE wa_contact_settings (
        contact_id INTEGER NOT NULL,
        app_id TEXT NOT NULL,
        name TEXT NOT NULL,
        value TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE wa_app_tokens (
        token TEXT PRIMARY KEY,
        contact_id INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE wa_contact_data_text (
        id INTEGER PRIMARY KEY,
        contact_id INTEGER NOT NULL,
        value TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE wa_contact_categories (
        contact_id INTEGER NOT NULL,
        category_id INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE wa_contact_category (
        id INTEGER PRIMARY KEY,
        cnt INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE wa_contact_events (
        id INTEGER PRIMARY KEY,
        contact_id INTEGER NOT NULL
    )
    """,
)


async def _scalar(session, sql: str):
    result = await session.execute(text(sql))
    return result.scalar_one()


@pytest.mark.asyncio
async def test_contact_delete_repository_cleans_legacy_contact_rows_in_source_order() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        for ddl in _AUXILIARY_DDL:
            await connection.exec_driver_sql(ddl)

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime(2026, 9, 20, 10, 0, 0)
    async with sessions() as session:
        session.add_all(
            [
                WaContactRow(
                    id=1,
                    name="Delete Me",
                    firstname="Delete",
                    is_user=1,
                    login="delete-me",
                    create_datetime=now,
                ),
                WaContactRow(
                    id=2,
                    name="Keep Me",
                    firstname="Keep",
                    is_user=1,
                    login="keep-me",
                    create_datetime=now,
                ),
                WaContactRow(
                    id=3,
                    name="Company Child",
                    firstname="Child",
                    company_contact_id=1,
                    create_datetime=now,
                ),
                WaContactEmailRow(
                    id=1,
                    contact_id=1,
                    email="delete@example.com",
                    ext="",
                    sort=0,
                    status="confirmed",
                ),
                WaContactEmailRow(
                    id=2,
                    contact_id=2,
                    email="keep@example.com",
                    ext="",
                    sort=0,
                    status="confirmed",
                ),
                WaContactDataRow(
                    id=1,
                    contact_id=1,
                    field="phone",
                    ext="",
                    value="+10000000001",
                    sort=0,
                    status=None,
                ),
                WaContactDataRow(
                    id=2,
                    contact_id=2,
                    field="phone",
                    ext="",
                    value="+10000000002",
                    sort=0,
                    status=None,
                ),
                WaContactRightRow(
                    group_id=-1,
                    app_id="team",
                    name="backend",
                    value=1,
                ),
                WaContactRightRow(
                    group_id=-2,
                    app_id="team",
                    name="backend",
                    value=1,
                ),
                WaUserGroupRow(contact_id=1, group_id=10, datetime=now),
                WaUserGroupRow(contact_id=2, group_id=10, datetime=now),
            ]
        )
        await session.execute(
            text(
                """
                INSERT INTO wa_verification_channel_assets(id, address)
                VALUES
                    (1, 'delete@example.com'),
                    (2, '+10000000001'),
                    (3, 'keep@example.com')
                """
            )
        )
        await session.execute(
            text(
                """
                INSERT INTO wa_contact_settings(contact_id, app_id, name, value)
                VALUES (1, 'team', 'x', '1'), (2, 'team', 'x', '2')
                """
            )
        )
        await session.execute(
            text(
                """
                INSERT INTO wa_app_tokens(token, contact_id)
                VALUES ('delete-token', 1), ('keep-token', 2)
                """
            )
        )
        await session.execute(
            text(
                """
                INSERT INTO wa_contact_data_text(id, contact_id, value)
                VALUES (1, 1, 'delete text'), (2, 2, 'keep text')
                """
            )
        )
        await session.execute(
            text(
                """
                INSERT INTO wa_contact_categories(contact_id, category_id)
                VALUES (1, 100), (1, 101), (2, 100)
                """
            )
        )
        await session.execute(
            text(
                """
                INSERT INTO wa_contact_category(id, cnt)
                VALUES (100, 2), (101, 1)
                """
            )
        )
        await session.execute(
            text(
                """
                INSERT INTO wa_contact_events(id, contact_id)
                VALUES (1, 1), (2, 2)
                """
            )
        )
        await session.commit()

    async with sessions() as session:
        repository = SQLAlchemyContactRepository(session)
        result = await repository.delete_batch(
            ContactDeletionBatch(contact_ids=(1,))
        )
        await session.commit()
        assert result.contact_ids == (1,)

    async with sessions() as session:
        assert await session.get(WaContactRow, 1) is None
        assert await session.get(WaContactRow, 2) is not None
        child = await session.get(WaContactRow, 3)
        assert child is not None
        assert child.company_contact_id == 0

        assert await _scalar(
            session,
            "SELECT COUNT(*) FROM wa_contact_rights WHERE group_id = -1",
        ) == 0
        assert await _scalar(
            session,
            "SELECT COUNT(*) FROM wa_contact_rights WHERE group_id = -2",
        ) == 1

        assert await _scalar(
            session,
            "SELECT COUNT(*) FROM wa_contact_emails WHERE contact_id = 1",
        ) == 0
        assert await _scalar(
            session,
            "SELECT COUNT(*) FROM wa_contact_data WHERE contact_id = 1",
        ) == 0
        assert await _scalar(
            session,
            "SELECT COUNT(*) FROM wa_user_groups WHERE contact_id = 1",
        ) == 0

        assert await _scalar(
            session,
            "SELECT COUNT(*) FROM wa_verification_channel_assets "
            "WHERE address IN ('delete@example.com', '+10000000001')",
        ) == 0
        assert await _scalar(
            session,
            "SELECT COUNT(*) FROM wa_verification_channel_assets "
            "WHERE address = 'keep@example.com'",
        ) == 1

        for table in (
            "wa_contact_settings",
            "wa_app_tokens",
            "wa_contact_data_text",
            "wa_contact_categories",
            "wa_contact_events",
        ):
            assert await _scalar(
                session,
                f"SELECT COUNT(*) FROM {table} WHERE contact_id = 1",
            ) == 0
            assert await _scalar(
                session,
                f"SELECT COUNT(*) FROM {table} WHERE contact_id = 2",
            ) == 1

        assert await _scalar(
            session,
            "SELECT cnt FROM wa_contact_category WHERE id = 100",
        ) == 1
        # Exact 4.2.0 recalcCounters() behavior: a category with no remaining
        # membership is absent from the UPDATE JOIN subquery and keeps old cnt.
        assert await _scalar(
            session,
            "SELECT cnt FROM wa_contact_category WHERE id = 101",
        ) == 1

    await engine.dispose()
