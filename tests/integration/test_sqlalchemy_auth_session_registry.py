from datetime import datetime, timedelta

import pytest

pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from gomazon_webasyst.application.auth_values import AuthSessionKey, SessionId
from gomazon_webasyst.contracts.auth import (
    AuthSessionRegistration,
    RegistryActive,
    RegistryAlreadyMissing,
    RegistryMissing,
    RegistryRevoked,
    RegistryTouched,
    RegistryWritten,
)
from gomazon_webasyst.infrastructure.auth.session_registry import SQLAlchemyAuthSessionRegistry
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base


class Clock:
    def __init__(self):
        self.now = datetime(2026, 1, 1, 12, 0, 0)

    def __call__(self):
        return self.now


@pytest.mark.asyncio
async def test_registry_register_check_touch_revoke_use_auth_session_key():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    clock = Clock()
    registry = SQLAlchemyAuthSessionRegistry(factory, clock=clock)
    key = AuthSessionKey(42, SessionId("sess-1"))
    registration = AuthSessionRegistration(
        key=key,
        credential_token="token-v1",
        user_agent="pytest",
    )

    written = await registry.register(registration)
    active = await registry.check(key)
    clock.now += timedelta(minutes=1)
    touched = await registry.touch(key)
    revoked = await registry.revoke(key)
    missing = await registry.check(key)
    missing_revoke = await registry.revoke(key)

    assert isinstance(written, RegistryWritten)
    assert isinstance(active, RegistryActive)
    assert isinstance(touched, RegistryTouched)
    assert isinstance(revoked, RegistryRevoked)
    assert isinstance(missing, RegistryMissing)
    assert isinstance(missing_revoke, RegistryAlreadyMissing)
    await engine.dispose()


@pytest.mark.asyncio
async def test_register_same_session_id_updates_existing_row_instead_of_duplicating():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    clock = Clock()
    registry = SQLAlchemyAuthSessionRegistry(factory, clock=clock)

    await registry.register(
        AuthSessionRegistration(
            key=AuthSessionKey(1, SessionId("same")),
            credential_token="old",
            user_agent="first",
        )
    )
    clock.now += timedelta(minutes=5)
    await registry.register(
        AuthSessionRegistration(
            key=AuthSessionKey(2, SessionId("same")),
            credential_token="new",
            user_agent="second",
        )
    )

    assert isinstance(await registry.check(AuthSessionKey(2, SessionId("same"))), RegistryActive)
    assert isinstance(await registry.check(AuthSessionKey(1, SessionId("same"))), RegistryMissing)
    await engine.dispose()
