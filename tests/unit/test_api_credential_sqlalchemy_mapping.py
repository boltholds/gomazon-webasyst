import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaApiAuthCodeRow,
    WaApiTokenRow,
)


def test_api_credential_orm_models_match_legacy_table_primary_key_and_lengths() -> None:
    assert WaApiAuthCodeRow.__tablename__ == "wa_api_auth_codes"
    assert WaApiTokenRow.__tablename__ == "wa_api_tokens"

    assert [column.name for column in WaApiAuthCodeRow.__table__.primary_key.columns] == ["code"]
    assert [column.name for column in WaApiTokenRow.__table__.primary_key.columns] == ["token"]

    assert WaApiAuthCodeRow.__table__.c.code.type.length == 32
    assert WaApiAuthCodeRow.__table__.c.client_id.type.length == 32
    assert WaApiTokenRow.__table__.c.token.type.length == 32
    assert WaApiTokenRow.__table__.c.client_id.type.length == 32


def test_api_credential_legacy_nullability_is_preserved_only_at_orm_boundary() -> None:
    assert not WaApiAuthCodeRow.__table__.c.code.nullable
    assert not WaApiAuthCodeRow.__table__.c.contact_id.nullable
    assert not WaApiAuthCodeRow.__table__.c.client_id.nullable
    assert not WaApiAuthCodeRow.__table__.c.scope.nullable
    assert not WaApiAuthCodeRow.__table__.c.expires.nullable

    assert not WaApiTokenRow.__table__.c.token.nullable
    assert not WaApiTokenRow.__table__.c.contact_id.nullable
    assert not WaApiTokenRow.__table__.c.client_id.nullable
    assert not WaApiTokenRow.__table__.c.scope.nullable
    assert not WaApiTokenRow.__table__.c.create_datetime.nullable
    assert WaApiTokenRow.__table__.c.last_use_datetime.nullable
    assert WaApiTokenRow.__table__.c.expires.nullable


def test_api_token_mapping_has_unique_contact_client_index() -> None:
    indexes = {index.name: index for index in WaApiTokenRow.__table__.indexes}
    contact_client = indexes["contact_client"]

    assert contact_client.unique
    assert [column.name for column in contact_client.columns] == ["contact_id", "client_id"]


@pytest.mark.asyncio
async def test_metadata_contains_legacy_api_credential_tables() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        names = set(await connection.run_sync(lambda sync: inspect(sync).get_table_names()))
    await engine.dispose()

    assert {"wa_api_auth_codes", "wa_api_tokens"} <= names
