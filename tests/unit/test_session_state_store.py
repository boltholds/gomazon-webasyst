from datetime import datetime, timedelta

import pytest

from gomazon_webasyst.application.auth_values import AuthSessionKey, SessionId
from gomazon_webasyst.contracts.auth import (
    AuthenticatedSubject,
    SessionAlreadyMissing,
    SessionCreateRequest,
    SessionCreated,
    SessionMetadata,
    SessionRevoked,
    SessionStateError,
    SessionStateResolved,
)
from gomazon_webasyst.contracts.enums import SessionStateErrorType
from gomazon_webasyst.infrastructure.sessions.memory import InMemorySessionStateStore


class Clock:
    def __init__(self):
        self.now = datetime(2026, 1, 1, 12, 0, 0)

    def __call__(self):
        return self.now


def make_request():
    return SessionCreateRequest(
        subject=AuthenticatedSubject(id=42, login="admin"),
        credential_token="token-v1",
        metadata=SessionMetadata(user_agent="pytest"),
    )


@pytest.mark.asyncio
async def test_create_returns_auth_session_key_and_resolve_accepts_session_id_vo():
    clock = Clock()
    store = InMemorySessionStateStore(
        session_id_factory=lambda: SessionId("sess-1"),
        clock=clock,
    )

    created = await store.create(make_request())
    resolved = await store.resolve(SessionId("sess-1"))

    assert isinstance(created, SessionCreated)
    assert created.state.key == AuthSessionKey(42, SessionId("sess-1"))
    assert isinstance(resolved, SessionStateResolved)
    assert resolved.state.key == created.state.key


@pytest.mark.asyncio
async def test_resolve_returns_explicit_not_found_instead_of_none():
    store = InMemorySessionStateStore(session_id_factory=lambda: SessionId("unused"))

    result = await store.resolve(SessionId("missing"))

    assert isinstance(result, SessionStateError)
    assert result.type is SessionStateErrorType.NOT_FOUND


@pytest.mark.asyncio
async def test_resolve_returns_expired_and_removes_state():
    clock = Clock()
    store = InMemorySessionStateStore(
        session_id_factory=lambda: SessionId("sess-1"),
        clock=clock,
        ttl=timedelta(minutes=30),
    )
    await store.create(make_request())
    clock.now += timedelta(minutes=31)

    expired = await store.resolve(SessionId("sess-1"))
    missing = await store.resolve(SessionId("sess-1"))

    assert isinstance(expired, SessionStateError)
    assert expired.type is SessionStateErrorType.EXPIRED
    assert isinstance(missing, SessionStateError)
    assert missing.type is SessionStateErrorType.NOT_FOUND


@pytest.mark.asyncio
async def test_revoke_uses_auth_session_key_and_is_idempotent():
    store = InMemorySessionStateStore(session_id_factory=lambda: SessionId("sess-1"))
    created = await store.create(make_request())
    key = created.state.key

    first = await store.revoke(key)
    second = await store.revoke(key)

    assert isinstance(first, SessionRevoked)
    assert isinstance(second, SessionAlreadyMissing)
