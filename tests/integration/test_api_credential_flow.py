import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.application.api_credential_values import ApiClientId, ApiScope
from gomazon_webasyst.composition.api_credentials import create_api_credential_use_cases
from gomazon_webasyst.contracts.api_credentials import (
    ApiAccessTokenAlreadyMissing,
    ApiAccessTokenIssued,
    ApiAccessTokenResolveRejected,
    ApiAccessTokenResolved,
    ApiAccessTokenRevoked,
    AuthorizationCodeExchanged,
    AuthorizationCodeIssued,
)
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.enums import ApiAccessTokenResolveRejectReason
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base


@pytest.mark.asyncio
async def test_webasyst_api_credential_vertical_flow() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    api = create_api_credential_use_cases(sessions)

    subject = AuthenticatedSubject(id=42, login="user")
    client = ApiClientId("client")

    issued_code = await api.issue_authorization_code(subject, client, ApiScope.of("shop"))
    assert isinstance(issued_code, AuthorizationCodeIssued)

    first_exchange = await api.exchange_authorization_code(issued_code.record.code, client)
    assert isinstance(first_exchange, AuthorizationCodeExchanged)

    second_exchange = await api.exchange_authorization_code(issued_code.record.code, client)
    assert isinstance(second_exchange, AuthorizationCodeExchanged)
    assert second_exchange.access_token == first_exchange.access_token

    implicit = await api.issue_implicit_api_access_token(subject, client, ApiScope.of("site"))
    assert isinstance(implicit, ApiAccessTokenIssued)
    assert implicit.access_token == first_exchange.access_token
    assert implicit.scope == ApiScope.of("site")

    resolved = await api.resolve_api_access_token(first_exchange.access_token)
    assert isinstance(resolved, ApiAccessTokenResolved)
    assert resolved.contact_id == 42
    assert resolved.client_id == client
    assert resolved.scope == ApiScope.of("site")

    revoked = await api.revoke_api_access_token(first_exchange.access_token)
    assert isinstance(revoked, ApiAccessTokenRevoked)

    second_revoke = await api.revoke_api_access_token(first_exchange.access_token)
    assert isinstance(second_revoke, ApiAccessTokenAlreadyMissing)

    missing = await api.resolve_api_access_token(first_exchange.access_token)
    assert isinstance(missing, ApiAccessTokenResolveRejected)
    assert missing.reason is ApiAccessTokenResolveRejectReason.MISSING

    await engine.dispose()
