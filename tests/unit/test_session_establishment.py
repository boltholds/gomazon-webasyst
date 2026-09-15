from datetime import datetime

import pytest

from gomazon_webasyst.application.auth_values import AuthSessionKey, SessionId
from gomazon_webasyst.application.session_establishment import BackendSessionEstablisher
from gomazon_webasyst.contracts.auth import (
    AuthIdentity,
    RegistryRevoked,
    RegistryWritten,
    SessionCreationError,
    SessionCreated,
    SessionMetadata,
    SessionRevoked,
    StoredAuthSession,
)
from gomazon_webasyst.contracts.enums import (
    BackendSessionEstablishmentRejectReason,
    SessionCreationErrorType,
)
from gomazon_webasyst.contracts.persistent_login import (
    BackendSessionEstablished,
    BackendSessionEstablishmentRejected,
)


IDENTITY = AuthIdentity(
    id=42,
    login="admin",
    password_hash="stored",
    is_user=1,
    create_datetime=datetime(2026, 1, 1),
)
KEY = AuthSessionKey(contact_id=42, session_id=SessionId("sess-1"))


class TokenFactory:
    def create(self, identity):
        assert identity == IDENTITY
        return "token-v1"


class SessionState:
    def __init__(self, create_result):
        self.create_result = create_result
        self.created = []
        self.revoked = []

    async def create(self, request):
        self.created.append(request)
        return self.create_result

    async def revoke(self, key):
        self.revoked.append(key)
        return SessionRevoked()


class Registry:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.registrations = []

    async def register(self, registration):
        if self.fail:
            raise RuntimeError("registry down")
        self.registrations.append(registration)
        return RegistryWritten()


def created_result():
    return SessionCreated(
        state=StoredAuthSession(
            key=KEY,
            subject={"id": 42, "login": "admin"},
            credential_token="token-v1",
            metadata=SessionMetadata(user_agent="pytest"),
            created_at=datetime(2026, 1, 1),
            last_seen_at=datetime(2026, 1, 1),
        )
    )


@pytest.mark.asyncio
async def test_establish_creates_state_and_registers_same_auth_session_key():
    state = SessionState(created_result())
    registry = Registry()
    establisher = BackendSessionEstablisher(
        session_state=state,
        session_registry=registry,
        token_factory=TokenFactory(),
    )

    result = await establisher.establish(
        IDENTITY,
        SessionMetadata(user_agent="pytest"),
    )

    assert isinstance(result, BackendSessionEstablished)
    assert result.session_key == KEY
    assert result.subject.id == 42
    assert state.created[0].credential_token == "token-v1"
    assert registry.registrations[0].key == KEY
    assert registry.registrations[0].credential_token == "token-v1"


@pytest.mark.asyncio
async def test_establish_maps_session_creation_error_to_typed_rejection():
    state = SessionState(SessionCreationError(type=SessionCreationErrorType.COLLISION))
    registry = Registry()
    establisher = BackendSessionEstablisher(
        session_state=state,
        session_registry=registry,
        token_factory=TokenFactory(),
    )

    result = await establisher.establish(IDENTITY, SessionMetadata())

    assert isinstance(result, BackendSessionEstablishmentRejected)
    assert result.reason is BackendSessionEstablishmentRejectReason.SESSION_UNAVAILABLE
    assert registry.registrations == []


@pytest.mark.asyncio
async def test_establish_revokes_fresh_state_then_propagates_registry_failure():
    state = SessionState(created_result())
    establisher = BackendSessionEstablisher(
        session_state=state,
        session_registry=Registry(fail=True),
        token_factory=TokenFactory(),
    )

    with pytest.raises(RuntimeError, match="registry down"):
        await establisher.establish(IDENTITY, SessionMetadata())

    assert state.revoked == [KEY]
