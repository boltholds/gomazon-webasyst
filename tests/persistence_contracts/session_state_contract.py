from datetime import timedelta
from typing import Protocol

from gomazon_webasyst.application.auth_values import AuthSessionKey, SessionId
from gomazon_webasyst.application.ports.session_state import SessionStateStore
from gomazon_webasyst.contracts.auth import (
    AuthenticatedSubject,
    SessionAlreadyMissing,
    SessionCreateRequest,
    SessionCreated,
    SessionCreationError,
    SessionMetadata,
    SessionRevoked,
    SessionStateError,
    SessionStateResolved,
)
from gomazon_webasyst.contracts.enums import SessionCreationErrorType, SessionStateErrorType


class SessionStateStoreContractHarness(Protocol):
    store: SessionStateStore
    session_id: SessionId
    ttl: timedelta

    async def advance(self, delta: timedelta) -> None: ...


def _request() -> SessionCreateRequest:
    return SessionCreateRequest(
        subject=AuthenticatedSubject(id=42, login="contract-user"),
        credential_token="credential-v1",
        metadata=SessionMetadata(user_agent="session-state-contract"),
    )


async def assert_session_state_store_contract(
    harness: SessionStateStoreContractHarness,
) -> None:
    created = await harness.store.create(_request())
    assert isinstance(created, SessionCreated)
    assert created.state.key == AuthSessionKey(
        contact_id=42,
        session_id=harness.session_id,
    )

    collision = await harness.store.create(_request())
    assert isinstance(collision, SessionCreationError)
    assert collision.type is SessionCreationErrorType.COLLISION

    resolved = await harness.store.resolve(harness.session_id)
    assert isinstance(resolved, SessionStateResolved)
    initial_last_seen = resolved.state.last_seen_at

    await harness.advance(harness.ttl)
    boundary = await harness.store.resolve(harness.session_id)
    assert isinstance(boundary, SessionStateResolved)
    assert boundary.state.last_seen_at > initial_last_seen

    wrong_key = AuthSessionKey(
        contact_id=999,
        session_id=harness.session_id,
    )
    wrong_revoke = await harness.store.revoke(wrong_key)
    assert isinstance(wrong_revoke, SessionAlreadyMissing)

    still_present = await harness.store.resolve(harness.session_id)
    assert isinstance(still_present, SessionStateResolved)

    await harness.advance(harness.ttl + timedelta(seconds=1))
    expired = await harness.store.resolve(harness.session_id)
    assert isinstance(expired, SessionStateError)
    assert expired.type is SessionStateErrorType.EXPIRED

    missing = await harness.store.resolve(harness.session_id)
    assert isinstance(missing, SessionStateError)
    assert missing.type is SessionStateErrorType.NOT_FOUND

    recreated = await harness.store.create(_request())
    assert isinstance(recreated, SessionCreated)
    assert recreated.state.key.session_id == harness.session_id

    revoked = await harness.store.revoke(recreated.state.key)
    assert isinstance(revoked, SessionRevoked)

    second_revoke = await harness.store.revoke(recreated.state.key)
    assert isinstance(second_revoke, SessionAlreadyMissing)
