from gomazon_webasyst.application.auth_values import AuthSessionKey, SessionId
from gomazon_webasyst.application.ports.auth_session_registry import AuthSessionRegistry
from gomazon_webasyst.application.ports.auth_subjects import AuthSubjectStore
from gomazon_webasyst.application.ports.credential_tokens import CredentialVersionTokenFactory
from gomazon_webasyst.application.ports.identity_directory import IdentityDirectory
from gomazon_webasyst.application.ports.login_policy import LoginPlanner
from gomazon_webasyst.application.ports.password_verifier import PasswordVerifier
from gomazon_webasyst.application.ports.session_state import SessionStateStore
from gomazon_webasyst.application.ports.session_validation import (
    SessionValidationDecision,
    SessionValidationPolicy,
    StrictSessionValidationPolicy,
)
from gomazon_webasyst.contracts.auth import (
    AuthSessionRegistration,
    AuthenticatedSubject,
    AuthenticationRejected,
    AuthenticationResult,
    AuthenticationSucceeded,
    BackendPasswordCredentials,
    IdentityResolutionError,
    LoginPlanError,
    LogoutResult,
    PasswordVerificationError,
    RegistryMissing,
    RegistryTouchMissing,
    SessionCreateRequest,
    SessionCreated,
    SessionCreationError,
    SessionResolutionError,
    SessionResolutionResult,
    SessionResolved,
    SessionStateError,
    SessionStateResolved,
    SubjectResolutionError,
)
from gomazon_webasyst.contracts.enums import (
    AuthenticationRejectType,
    LogoutStatus,
    SessionResolutionErrorType,
    SessionStateErrorType,
    SubjectResolutionErrorType,
)


class AuthenticateBackendPassword:
    def __init__(
        self,
        *,
        planner: LoginPlanner,
        identity_directory: IdentityDirectory,
        password_verifier: PasswordVerifier,
        token_factory: CredentialVersionTokenFactory,
        session_state: SessionStateStore,
        session_registry: AuthSessionRegistry,
    ) -> None:
        self._planner = planner
        self._identity_directory = identity_directory
        self._password_verifier = password_verifier
        self._token_factory = token_factory
        self._session_state = session_state
        self._session_registry = session_registry

    async def __call__(self, credentials: BackendPasswordCredentials) -> AuthenticationResult:
        plan_result = self._planner.plan(credentials.identifier, credentials.login_context)
        if isinstance(plan_result, LoginPlanError):
            return AuthenticationRejected(type=AuthenticationRejectType.POLICY_REJECTED)

        identity_result = await self._identity_directory.resolve(plan_result.plan)
        if isinstance(identity_result, IdentityResolutionError):
            return AuthenticationRejected(type=AuthenticationRejectType.INVALID_CREDENTIALS)

        identity = identity_result.identity
        if identity.is_user <= 0:
            return AuthenticationRejected(type=AuthenticationRejectType.SUBJECT_DISABLED)

        password_result = self._password_verifier.verify(
            credentials.password,
            identity.password_hash,
        )
        if isinstance(password_result, PasswordVerificationError):
            return AuthenticationRejected(type=AuthenticationRejectType.INVALID_CREDENTIALS)

        subject = AuthenticatedSubject(id=identity.id, login=identity.login)
        token = self._token_factory.create(identity)
        created = await self._session_state.create(
            SessionCreateRequest(
                subject=subject,
                credential_token=token,
                metadata=credentials.session_metadata,
            )
        )
        if isinstance(created, SessionCreationError):
            return AuthenticationRejected(type=AuthenticationRejectType.SESSION_UNAVAILABLE)
        assert isinstance(created, SessionCreated)

        registration = AuthSessionRegistration(
            key=created.state.key,
            credential_token=token,
            user_agent=credentials.session_metadata.user_agent,
        )
        try:
            await self._session_registry.register(registration)
        except Exception:
            await self._session_state.revoke(created.state.key)
            raise

        return AuthenticationSucceeded(subject=subject, session_key=created.state.key)


class ResolveBackendSession:
    def __init__(
        self,
        *,
        session_state: SessionStateStore,
        subject_store: AuthSubjectStore,
        token_factory: CredentialVersionTokenFactory,
        session_registry: AuthSessionRegistry,
        validation_policy: SessionValidationPolicy = StrictSessionValidationPolicy(),
    ) -> None:
        self._session_state = session_state
        self._subject_store = subject_store
        self._token_factory = token_factory
        self._session_registry = session_registry
        self._validation_policy = validation_policy

    async def __call__(self, session_id: SessionId) -> SessionResolutionResult:
        state_result = await self._session_state.resolve(session_id)
        if isinstance(state_result, SessionStateError):
            mapped = (
                SessionResolutionErrorType.EXPIRED
                if state_result.type is SessionStateErrorType.EXPIRED
                else SessionResolutionErrorType.NOT_FOUND
            )
            return SessionResolutionError(type=mapped)
        assert isinstance(state_result, SessionStateResolved)
        state = state_result.state
        key = state.key

        if self._validation_policy.decide(state) is SessionValidationDecision.TRUST_STORED:
            return SessionResolved(subject=state.subject, session_key=key)

        subject_result = await self._subject_store.get(key.contact_id)
        if isinstance(subject_result, SubjectResolutionError):
            await self._revoke_both(key)
            mapped = (
                SessionResolutionErrorType.SUBJECT_DISABLED
                if subject_result.type is SubjectResolutionErrorType.DISABLED
                else SessionResolutionErrorType.SUBJECT_UNAVAILABLE
            )
            return SessionResolutionError(type=mapped)

        identity = subject_result.identity
        if self._token_factory.create(identity) != state.credential_token:
            await self._revoke_both(key)
            return SessionResolutionError(type=SessionResolutionErrorType.CREDENTIALS_CHANGED)

        registry_result = await self._session_registry.check(key)
        if isinstance(registry_result, RegistryMissing):
            await self._session_state.revoke(key)
            return SessionResolutionError(type=SessionResolutionErrorType.REVOKED)

        touch_result = await self._session_registry.touch(key)
        if isinstance(touch_result, RegistryTouchMissing):
            await self._session_state.revoke(key)
            return SessionResolutionError(type=SessionResolutionErrorType.REVOKED)

        return SessionResolved(
            subject=AuthenticatedSubject(id=identity.id, login=identity.login),
            session_key=key,
        )

    async def _revoke_both(self, key: AuthSessionKey) -> None:
        await self._session_state.revoke(key)
        await self._session_registry.revoke(key)


class LogoutBackendSession:
    def __init__(
        self,
        *,
        session_state: SessionStateStore,
        session_registry: AuthSessionRegistry,
    ) -> None:
        self._session_state = session_state
        self._session_registry = session_registry

    async def __call__(self, session_id: SessionId) -> LogoutResult:
        state_result = await self._session_state.resolve(session_id)
        if isinstance(state_result, SessionStateError):
            return LogoutResult(status=LogoutStatus.ALREADY_MISSING)
        assert isinstance(state_result, SessionStateResolved)
        key = state_result.state.key
        await self._session_state.revoke(key)
        await self._session_registry.revoke(key)
        return LogoutResult(status=LogoutStatus.REVOKED)
