from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import uuid4

from gomazon_webasyst.application.auth_values import AuthSessionKey, SessionId
from gomazon_webasyst.contracts.auth import (
    SessionAlreadyMissing,
    SessionCreateRequest,
    SessionCreated,
    SessionCreationError,
    SessionCreationResult,
    SessionRevocationResult,
    SessionRevoked,
    SessionStateError,
    SessionStateResolved,
    SessionStateResolution,
    StoredAuthSession,
)
from gomazon_webasyst.contracts.enums import SessionCreationErrorType, SessionStateErrorType


class InMemorySessionStateStore:
    def __init__(
        self,
        session_id_factory: Callable[[], SessionId] = lambda: SessionId(uuid4().hex),
        clock: Callable[[], datetime] = datetime.now,
        ttl: timedelta = timedelta(minutes=30),
    ) -> None:
        self._session_id_factory = session_id_factory
        self._clock = clock
        self._ttl = ttl
        self._states: dict[SessionId, StoredAuthSession] = {}

    async def create(self, request: SessionCreateRequest) -> SessionCreationResult:
        session_id = self._session_id_factory()
        if session_id in self._states:
            return SessionCreationError(type=SessionCreationErrorType.COLLISION)
        now = self._clock()
        state = StoredAuthSession(
            key=AuthSessionKey(contact_id=request.subject.id, session_id=session_id),
            subject=request.subject,
            credential_token=request.credential_token,
            metadata=request.metadata,
            created_at=now,
            last_seen_at=now,
        )
        self._states[session_id] = state
        return SessionCreated(state=state)

    async def resolve(self, session_id: SessionId) -> SessionStateResolution:
        if session_id not in self._states:
            return SessionStateError(type=SessionStateErrorType.NOT_FOUND)
        state = self._states[session_id]
        now = self._clock()
        if now - state.last_seen_at > self._ttl:
            del self._states[session_id]
            return SessionStateError(type=SessionStateErrorType.EXPIRED)
        refreshed = state.model_copy(update={"last_seen_at": now})
        self._states[session_id] = refreshed
        return SessionStateResolved(state=refreshed)

    async def revoke(self, key: AuthSessionKey) -> SessionRevocationResult:
        if key.session_id not in self._states:
            return SessionAlreadyMissing()
        state = self._states[key.session_id]
        if state.key != key:
            return SessionAlreadyMissing()
        del self._states[key.session_id]
        return SessionRevoked()
