import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.application.contact_deletion import ContactDeletionBatch
from gomazon_webasyst.infrastructure.contacts_app.sqlalchemy.rights import (
    SQLAlchemyContactsPrivateRightsCleaner,
)


@pytest.mark.asyncio
async def test_contacts_private_rights_cleanup_deletes_only_personal_rows() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.exec_driver_sql(
            "CREATE TABLE contacts_rights ("
            "group_id INTEGER NOT NULL, "
            "category_id INTEGER NOT NULL, "
            "writable INTEGER NOT NULL DEFAULT 0, "
            "PRIMARY KEY (group_id, category_id))"
        )
        await connection.exec_driver_sql(
            "INSERT INTO contacts_rights(group_id, category_id, writable) "
            "VALUES (-7, 1, 1), (-8, 2, 0), (-9, 3, 1), (4, 4, 1)"
        )

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cleaner = SQLAlchemyContactsPrivateRightsCleaner(sessions)

    result = await cleaner.delete_for_contacts(
        ContactDeletionBatch(contact_ids=(7, 8, 7))
    )

    assert result.contact_ids == (7, 8, 7)
    async with sessions() as session:
        rows = await session.execute(
            text(
                "SELECT group_id, category_id, writable "
                "FROM contacts_rights ORDER BY group_id, category_id"
            )
        )
        assert [tuple(row) for row in rows] == [
            (-9, 3, 1),
            (4, 4, 1),
        ]

    await engine.dispose()
