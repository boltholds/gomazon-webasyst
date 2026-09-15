import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaContactRightRow,
    WaGroupRow,
    WaUserGroupRow,
)


def test_acl_orm_models_match_legacy_table_and_primary_key_shapes() -> None:
    assert WaGroupRow.__tablename__ == "wa_group"
    assert WaUserGroupRow.__tablename__ == "wa_user_groups"
    assert WaContactRightRow.__tablename__ == "wa_contact_rights"

    assert [column.name for column in WaGroupRow.__table__.primary_key.columns] == ["id"]
    assert [column.name for column in WaUserGroupRow.__table__.primary_key.columns] == [
        "contact_id",
        "group_id",
    ]
    assert [column.name for column in WaContactRightRow.__table__.primary_key.columns] == [
        "group_id",
        "app_id",
        "name",
    ]


def test_legacy_nullable_columns_remain_nullable_only_at_orm_boundary() -> None:
    assert WaGroupRow.__table__.c.icon.nullable
    assert WaGroupRow.__table__.c.sort.nullable
    assert WaGroupRow.__table__.c.description.nullable
    assert WaUserGroupRow.__table__.c.datetime.nullable
    assert not WaContactRightRow.__table__.c.value.nullable


@pytest.mark.asyncio
async def test_metadata_contains_acl_tables() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        names = set(await connection.run_sync(lambda sync: inspect(sync).get_table_names()))
    await engine.dispose()
    assert {"wa_group", "wa_user_groups", "wa_contact_rights"} <= names
