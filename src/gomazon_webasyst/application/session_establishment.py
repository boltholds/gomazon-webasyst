from gomazon_webasyst.application.ports.auth_session_registry import AuthSessionRegistry
from gomazon_webasyst.application.ports.credential_tokens import CredentialVersionTokenFactory
from gomazon_webasyst.application.ports.session_state import SessionStateStore
from gomazon_webasyst.contracts.auth import (
    AuthIdentity,
    AuthSessionRegistration,
    AuthenticatedSubject,
    SessionCreateRequest,
    SessionCreated,
    SessionCreationError,
    SessionMetadata,
)
from gomazon_webasyst.contracts.enums import BackendSessionEstablishmentRejectReason
from gomazon_webasyst.contracts.persistent_login import (
    BackendSessionEstablished,
    BackendSessionEstablishmentRejected,
    BackendSessionEstablishmentResult,
)


class BackendSessionEstablisher:
    def __init__(
        self,
        *,
        session_state: SessionStateStore,
        session_registry: AuthSessionRegistry,
        token_factory: CredentialVersionTokenFactory,
    ) -> None:
        self._session_state = session_state
        self._session_registry = session_registry
        self._token_factory = token_factory

    async def establish(
        self,
        identity: AuthIdentity,
        metadata: SessionMetadata,
    ) -> BackendSessionEstablishmentResult:
        subject = AuthenticatedSubject(id=identity.id, login=identity.login)
        token = self._token_factory.create(identity)
        created = await self._session_state.create(
            SessionCreateRequest(
                subject=subject,
                credential_token=token,
                metadata=metadata,
            )
        )
        if isinstance(created, SessionCreationError):
            return BackendSessionEstablishmentRejected(
                reason=BackendSessionEstablishmentRejectReason.SESSION_UNAVAILABLE
            )
        assert isinstance(created, SessionCreated)

        registration = AuthSessionRegistration(
            key=created.state.key,
            credential_token=token,
            user_agent=metadata.user_agent,
        )
        try:
            await self._session_registry.register(registration)
        except Exception:
            await self._session_state.revoke(created.state.key)
            raise

        return BackendSessionEstablished(subject=subject, session_key=created.state.key)
