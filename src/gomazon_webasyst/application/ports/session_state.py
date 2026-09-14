from typing import Protocol

from gomazon_webasyst.application.auth_values import AuthSessionKey, SessionId
from gomazon_webasyst.contracts.auth import (
    SessionCreateRequest,
    SessionCreationResult,
    SessionRevocationResult,
    SessionStateResolution,
)


class SessionStateStore(Protocol):
    async def create(self, request: SessionCreateRequest) -> SessionCreationResult: ...
    async def resolve(self, session_id: SessionId) -> SessionStateResolution: ...
    async def revoke(self, key: AuthSessionKey) -> SessionRevocationResult: ...
