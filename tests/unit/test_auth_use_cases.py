from datetime import datetime

import pytest
from pydantic import SecretStr

from gomazon_webasyst.application.auth import (
    AuthenticateBackendPassword,
    LogoutBackendSession,
    ResolveBackendSession,
)
from gomazon_webasyst.application.auth_values import AuthSessionKey, SessionId
from gomazon_webasyst.contracts.auth import (
    AuthIdentity,
    AuthenticatedSubject,
    AuthenticationRejected,
    AuthenticationSucceeded,
    BackendPasswordCredentials,
    IdentityKey,
    IdentityLookupPlan,
    IdentityResolved,
    IdentityResolutionError,
    LoginPlanBuilt,
    LoginPolicyContext,
    PasswordAccepted,
    PasswordVerificationError,
    RegistryActive,
    RegistryMissing,
    RegistryTouched,
    RegistryWritten,
    SessionMetadata,
    SessionResolutionError,
    SessionResolved,
    SubjectResolved,
    SubjectResolutionError,
)
from gomazon_webasyst.contracts.enums import (
    AuthenticationRejectType,
    IdentityResolutionErrorType,
    PasswordVerificationErrorType,
    SessionResolutionErrorType,
    SubjectResolutionErrorType,
)
from gomazon_webasyst.infrastructure.sessions.memory import InMemorySessionStateStore


IDENTITY = AuthIdentity(
    id=42,
    login="admin",
    password_hash="stored",
    is_user=1,
    create_datetime=datetime(2026, 1, 1),
)
PLAN = IdentityLookupPlan(keys=(IdentityKey(scheme="login", value="admin"),))


class Planner:
    def plan(self, value, context):
        return LoginPlanBuilt(plan=PLAN)


class Directory:
    def __init__(self, result):
        self.result = result

    async def resolve(self, plan):
        return self.result


class Verifier:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def verify(self, candidate, stored_hash):
        self.calls += 1
        return self.result


class TokenFactory:
    def __init__(self, token="token-v1"):
        self.token = token

    def create(self, identity):
        return self.token


class SubjectStore:
    def __init__(self, result):
        self.result = result

    async def get(self, subject_id):
        return self.result


class Registry:
    def __init__(self):
        self.registrations = []
        self.checked = []
        self.touched = []
        self.revoked = []
        self.check_result = RegistryActive()
        self.touch_result = RegistryTouched()
        self.raise_on_register = False

    async def register(self, registration):
        if self.raise_on_register:
            raise RuntimeError("db down")
        self.registrations.append(registration)
        return RegistryWritten()

    async def check(self, key):
        self.checked.append(key)
        return self.check_result

    async def touch(self, key):
        self.touched.append(key)
        return self.touch_result

    async def revoke(self, key):
        from gomazon_webasyst.contracts.auth import RegistryRevoked

        self.revoked.append(key)
        return RegistryRevoked()


def credentials():
    return BackendPasswordCredentials(
        identifier="admin",
        password=SecretStr("secret"),
        login_context=LoginPolicyContext(enabled_schemes=("login", "email")),
        session_metadata=SessionMetadata(user_agent="pytest"),
    )


def make_auth(directory_result, password_result, *, registry=None, store=None):
    return AuthenticateBackendPassword(
        planner=Planner(),
        identity_directory=Directory(directory_result),
        password_verifier=Verifier(password_result),
        token_factory=TokenFactory(),
        session_state=store or InMemorySessionStateStore(session_id_factory=lambda: SessionId("sess-1")),
        session_registry=registry or Registry(),
    )


@pytest.mark.asyncio
async def test_auth_identity_miss_is_invalid_credentials_not_none():
    use_case = make_auth(
        IdentityResolutionError(type=IdentityResolutionErrorType.NOT_FOUND),
        PasswordAccepted(),
    )

    result = await use_case(credentials())

    assert isinstance(result, AuthenticationRejected)
    assert result.type is AuthenticationRejectType.INVALID_CREDENTIALS


@pytest.mark.asyncio
async def test_auth_wrong_password_is_explicit_rejection():
    use_case = make_auth(
        IdentityResolved(identity=IDENTITY, matched_key=PLAN.keys[0]),
        PasswordVerificationError(type=PasswordVerificationErrorType.INVALID),
    )

    result = await use_case(credentials())

    assert isinstance(result, AuthenticationRejected)
    assert result.type is AuthenticationRejectType.INVALID_CREDENTIALS


@pytest.mark.asyncio
async def test_auth_rejects_non_backend_user_even_if_custom_directory_returns_it():
    disabled = IDENTITY.model_copy(update={"is_user": 0})
    use_case = make_auth(
        IdentityResolved(identity=disabled, matched_key=PLAN.keys[0]),
        PasswordAccepted(),
    )

    result = await use_case(credentials())

    assert isinstance(result, AuthenticationRejected)
    assert result.type is AuthenticationRejectType.SUBJECT_DISABLED


@pytest.mark.asyncio
async def test_successful_auth_creates_state_and_registers_same_auth_session_key():
    registry = Registry()
    use_case = make_auth(
        IdentityResolved(identity=IDENTITY, matched_key=PLAN.keys[0]),
        PasswordAccepted(),
        registry=registry,
    )

    result = await use_case(credentials())

    assert isinstance(result, AuthenticationSucceeded)
    assert result.session_key == AuthSessionKey(42, SessionId("sess-1"))
    assert registry.registrations[0].key == result.session_key
    assert registry.registrations[0].credential_token == "token-v1"


@pytest.mark.asyncio
async def test_registry_infrastructure_failure_revokes_just_created_session_then_propagates():
    registry = Registry()
    registry.raise_on_register = True
    store = InMemorySessionStateStore(session_id_factory=lambda: SessionId("sess-1"))
    use_case = make_auth(
        IdentityResolved(identity=IDENTITY, matched_key=PLAN.keys[0]),
        PasswordAccepted(),
        registry=registry,
        store=store,
    )

    with pytest.raises(RuntimeError, match="db down"):
        await use_case(credentials())

    from gomazon_webasyst.contracts.auth import SessionStateError
    from gomazon_webasyst.contracts.enums import SessionStateErrorType

    missing = await store.resolve(SessionId("sess-1"))
    assert isinstance(missing, SessionStateError)
    assert missing.type is SessionStateErrorType.NOT_FOUND


async def create_state(token="token-v1"):
    store = InMemorySessionStateStore(session_id_factory=lambda: SessionId("sess-1"))
    from gomazon_webasyst.contracts.auth import SessionCreateRequest

    await store.create(
        SessionCreateRequest(
            subject=AuthenticatedSubject(id=42, login="admin"),
            credential_token=token,
            metadata=SessionMetadata(),
        )
    )
    return store


@pytest.mark.asyncio
async def test_resolve_session_returns_credentials_changed_and_revokes_state_on_token_mismatch():
    store = await create_state(token="old")
    registry = Registry()
    use_case = ResolveBackendSession(
        session_state=store,
        subject_store=SubjectStore(SubjectResolved(identity=IDENTITY)),
        token_factory=TokenFactory("new"),
        session_registry=registry,
    )

    result = await use_case(SessionId("sess-1"))

    assert isinstance(result, SessionResolutionError)
    assert result.type is SessionResolutionErrorType.CREDENTIALS_CHANGED
    assert registry.revoked == [AuthSessionKey(42, SessionId("sess-1"))]


@pytest.mark.asyncio
async def test_resolve_session_returns_revoked_when_registry_row_is_missing():
    store = await create_state()
    registry = Registry()
    registry.check_result = RegistryMissing()
    use_case = ResolveBackendSession(
        session_state=store,
        subject_store=SubjectStore(SubjectResolved(identity=IDENTITY)),
        token_factory=TokenFactory(),
        session_registry=registry,
    )

    result = await use_case(SessionId("sess-1"))

    assert isinstance(result, SessionResolutionError)
    assert result.type is SessionResolutionErrorType.REVOKED


@pytest.mark.asyncio
async def test_resolve_session_maps_disabled_subject_and_success_touches_registry():
    disabled_store = await create_state()
    disabled_case = ResolveBackendSession(
        session_state=disabled_store,
        subject_store=SubjectStore(
            SubjectResolutionError(type=SubjectResolutionErrorType.DISABLED)
        ),
        token_factory=TokenFactory(),
        session_registry=Registry(),
    )
    disabled = await disabled_case(SessionId("sess-1"))
    assert isinstance(disabled, SessionResolutionError)
    assert disabled.type is SessionResolutionErrorType.SUBJECT_DISABLED

    store = await create_state()
    registry = Registry()
    success_case = ResolveBackendSession(
        session_state=store,
        subject_store=SubjectStore(SubjectResolved(identity=IDENTITY)),
        token_factory=TokenFactory(),
        session_registry=registry,
    )
    success = await success_case(SessionId("sess-1"))

    assert isinstance(success, SessionResolved)
    assert registry.touched == [AuthSessionKey(42, SessionId("sess-1"))]


@pytest.mark.asyncio
async def test_logout_resolves_key_and_is_idempotent():
    store = await create_state()
    registry = Registry()
    logout = LogoutBackendSession(session_state=store, session_registry=registry)

    first = await logout(SessionId("sess-1"))
    second = await logout(SessionId("sess-1"))

    assert first.status.value == "revoked"
    assert second.status.value == "already_missing"
    assert registry.revoked == [AuthSessionKey(42, SessionId("sess-1"))]
