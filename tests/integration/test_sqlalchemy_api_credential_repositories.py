from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.application.api_credential_values import (
    ApiAccessToken,
    ApiClientId,
    ApiScope,
    AuthorizationCode,
)
from gomazon_webasyst.application.ports.api_credentials import (
    ApiTokenAlreadyMissing,
    ApiTokenForSubjectClientFound,
    ApiTokenRevoked,
    ApiTokenScopeUpdated,
    ApiTokenStored,
    ApiTokenSubjectClientCollision,
    ApiTokenTouched,
    ApiTokenValueCollision,
    AuthorizationCodeAlreadyMissing,
    AuthorizationCodeDeleted,
    AuthorizationCodeFound,
    AuthorizationCodeStored,
)
from gomazon_webasyst.compatibility.webasyst.api_credentials import LegacyApiScopeCodec
from gomazon_webasyst.contracts.api_credentials import (
    ApiTokenNeverExpires,
    ApiTokenNeverUsed,
    ApiTokenResolved,
    StoredApiAccessToken,
    StoredAuthorizationCode,
)
from gomazon_webasyst.infrastructure.api_credentials.sqlalchemy.repositories import (
    SQLAlchemyApiTokenRepository,
    SQLAlchemyAuthorizationCodeRepository,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base


async def _database():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_authorization_code_repository_round_trip_and_idempotent_delete() -> None:
    engine, sessions = await _database()
    now = datetime(2026, 9, 15, 12, 0, 0)
    record = StoredAuthorizationCode(
        code=AuthorizationCode("a" * 32),
        contact_id=42,
        client_id=ApiClientId("client"),
        scope=ApiScope.of("shop", "site"),
        expires_at=now + timedelta(seconds=180),
    )

    async with sessions() as session:
        repo = SQLAlchemyAuthorizationCodeRepository(session, LegacyApiScopeCodec())
        created = await repo.create(record)
        assert isinstance(created, AuthorizationCodeStored)
        await session.commit()

    async with sessions() as session:
        repo = SQLAlchemyAuthorizationCodeRepository(session, LegacyApiScopeCodec())
        resolved = await repo.resolve(record.code)
        assert isinstance(resolved, AuthorizationCodeFound)
        assert resolved.record == record

        deleted = await repo.delete(record.code)
        assert isinstance(deleted, AuthorizationCodeDeleted)
        await session.commit()

    async with sessions() as session:
        repo = SQLAlchemyAuthorizationCodeRepository(session, LegacyApiScopeCodec())
        missing = await repo.resolve(record.code)
        assert missing.code == record.code
        already_missing = await repo.delete(record.code)
        assert isinstance(already_missing, AuthorizationCodeAlreadyMissing)

    await engine.dispose()


@pytest.mark.asyncio
async def test_api_token_repository_normalizes_nullable_state_and_supports_mutations() -> None:
    engine, sessions = await _database()
    now = datetime(2026, 9, 15, 12, 0, 0)
    token = ApiAccessToken("b" * 32)
    record = StoredApiAccessToken(
        token=token,
        contact_id=42,
        client_id=ApiClientId("client"),
        scope=ApiScope.of("shop"),
        created_at=now,
        last_use=ApiTokenNeverUsed(),
        expiry=ApiTokenNeverExpires(),
    )

    async with sessions() as session:
        repo = SQLAlchemyApiTokenRepository(session, LegacyApiScopeCodec())
        created = await repo.create(record)
        assert isinstance(created, ApiTokenStored)
        await session.commit()

    async with sessions() as session:
        repo = SQLAlchemyApiTokenRepository(session, LegacyApiScopeCodec())
        resolved = await repo.resolve(token)
        assert isinstance(resolved, ApiTokenResolved)
        assert isinstance(resolved.record.expiry, ApiTokenNeverExpires)
        assert isinstance(resolved.record.last_use, ApiTokenNeverUsed)

        subject_client = await repo.find_for_subject_client(42, ApiClientId("client"))
        assert isinstance(subject_client, ApiTokenForSubjectClientFound)
        assert subject_client.record.token == token

        scope = ApiScope.of("site", "shop")
        updated = await repo.update_scope(token, scope)
        assert isinstance(updated, ApiTokenScopeUpdated)

        touched_at = now + timedelta(minutes=1)
        touched = await repo.touch_last_use(token, touched_at)
        assert isinstance(touched, ApiTokenTouched)
        await session.commit()

    async with sessions() as session:
        repo = SQLAlchemyApiTokenRepository(session, LegacyApiScopeCodec())
        resolved = await repo.resolve(token)
        assert isinstance(resolved, ApiTokenResolved)
        assert resolved.record.scope == ApiScope.of("site", "shop")
        assert resolved.record.last_use.at == now + timedelta(minutes=1)

        revoked = await repo.revoke(token)
        assert isinstance(revoked, ApiTokenRevoked)
        await session.commit()

    async with sessions() as session:
        repo = SQLAlchemyApiTokenRepository(session, LegacyApiScopeCodec())
        already_missing = await repo.revoke(token)
        assert isinstance(already_missing, ApiTokenAlreadyMissing)

    await engine.dispose()


@pytest.mark.asyncio
async def test_api_token_repository_classifies_unique_collisions() -> None:
    engine, sessions = await _database()
    now = datetime(2026, 9, 15, 12, 0, 0)

    def record(token: str, contact_id: int, client_id: str) -> StoredApiAccessToken:
        return StoredApiAccessToken(
            token=ApiAccessToken(token),
            contact_id=contact_id,
            client_id=ApiClientId(client_id),
            scope=ApiScope.of("shop"),
            created_at=now,
            last_use=ApiTokenNeverUsed(),
            expiry=ApiTokenNeverExpires(),
        )

    async with sessions() as session:
        repo = SQLAlchemyApiTokenRepository(session, LegacyApiScopeCodec())
        assert isinstance(await repo.create(record("a" * 32, 42, "client")), ApiTokenStored)
        await session.commit()

    async with sessions() as session:
        repo = SQLAlchemyApiTokenRepository(session, LegacyApiScopeCodec())
        subject_client = await repo.create(record("b" * 32, 42, "client"))
        assert isinstance(subject_client, ApiTokenSubjectClientCollision)

        token_value = await repo.create(record("a" * 32, 43, "other-client"))
        assert isinstance(token_value, ApiTokenValueCollision)

    await engine.dispose()
