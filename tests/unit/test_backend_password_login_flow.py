from datetime import timedelta
from importlib import import_module

import pytest
from pydantic import SecretStr

from gomazon_webasyst.application.auth_values import AuthSessionKey, SessionId
from gomazon_webasyst.application.backend_session_bridge.composites.requests import (
    BackendPasswordLoginRequest,
)
from gomazon_webasyst.application.persistent_values import (
    PersistentCredential,
    PersistentCredentialLifetime,
)
from gomazon_webasyst.contracts.auth import (
    AuthenticatedSubject,
    AuthenticationRejected,
    AuthenticationSucceeded,
    BackendPasswordCredentials,
    LoginPolicyContext,
)
from gomazon_webasyst.contracts.backend_session_bridge import (
    BackendPasswordLoginRejected,
    BackendPasswordLoginSucceeded,
    IssueSessionCredential,
    KeepSessionCredential,
)
from gomazon_webasyst.contracts.enums import (
    AuthenticationRejectType,
    BackendLoginPersistenceStatus,
    PersistentCredentialIssueRejectReason,
    PersistentLoginMode,
    RememberIntent,
)
from gomazon_webasyst.contracts.persistent_login import (
    KeepPersistentCredential,
    PersistentCredentialIssueRejected,
    PersistentCredentialIssued,
    RefreshPersistentCredential,
)


SUBJECT = AuthenticatedSubject(id=42, login="admin")
KEY = AuthSessionKey(contact_id=42, session_id=SessionId("sess-1"))
CREDENTIALS = BackendPasswordCredentials(
    identifier="admin",
    password=SecretStr("secret"),
    login_context=LoginPolicyContext(enabled_schemes=("login",)),
)
PERSISTENT = PersistentCredential("token")
LIFETIME = PersistentCredentialLifetime(timedelta(days=30))


def _flow_class():
    try:
        return import_module(
            "gomazon_webasyst.application.backend_session_bridge.composites.login"
        ).BackendPasswordLoginFlow
    except (ModuleNotFoundError, AttributeError) as error:
        pytest.fail(f"password login flow missing: {error}")


class Authenticator:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def __call__(self, credentials):
        self.calls.append(credentials)
        return self.result


class Issuer:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def __call__(self, subject):
        self.calls.append(subject)
        return self.result


class FailIfCalledIssuer:
    async def __call__(self, subject):
        raise AssertionError("persistent issuer must not be called")


def request(
    remember: RememberIntent,
    *,
    mode: PersistentLoginMode = PersistentLoginMode.ENABLED,
):
    return BackendPasswordLoginRequest(
        credentials=CREDENTIALS,
        remember_intent=remember,
        persistent_login_mode=mode,
    )


@pytest.mark.asyncio
async def test_primary_auth_rejection_never_calls_persistent_issuer() -> None:
    flow = _flow_class()(
        authenticate_backend_password=Authenticator(
            AuthenticationRejected(type=AuthenticationRejectType.INVALID_CREDENTIALS)
        ),
        issue_persistent_credential=FailIfCalledIssuer(),
    )

    result = await flow(request(RememberIntent.PERSIST))

    assert isinstance(result, BackendPasswordLoginRejected)
    assert result.authentication_type is AuthenticationRejectType.INVALID_CREDENTIALS
    assert isinstance(result.session_disposition, KeepSessionCredential)
    assert isinstance(result.persistent_disposition, KeepPersistentCredential)


@pytest.mark.asyncio
async def test_session_only_success_never_calls_persistent_issuer() -> None:
    flow = _flow_class()(
        authenticate_backend_password=Authenticator(
            AuthenticationSucceeded(subject=SUBJECT, session_key=KEY)
        ),
        issue_persistent_credential=FailIfCalledIssuer(),
    )

    result = await flow(request(RememberIntent.SESSION_ONLY))

    assert isinstance(result, BackendPasswordLoginSucceeded)
    assert result.session_disposition == IssueSessionCredential(
        session_id=KEY.session_id
    )
    assert isinstance(result.persistent_disposition, KeepPersistentCredential)
    assert result.persistence_status is BackendLoginPersistenceStatus.SESSION_ONLY


@pytest.mark.asyncio
async def test_persistent_login_disabled_never_calls_persistent_issuer() -> None:
    flow = _flow_class()(
        authenticate_backend_password=Authenticator(
            AuthenticationSucceeded(subject=SUBJECT, session_key=KEY)
        ),
        issue_persistent_credential=FailIfCalledIssuer(),
    )

    result = await flow(
        request(RememberIntent.PERSIST, mode=PersistentLoginMode.DISABLED)
    )

    assert isinstance(result, BackendPasswordLoginSucceeded)
    assert isinstance(result.persistent_disposition, KeepPersistentCredential)
    assert result.persistence_status is BackendLoginPersistenceStatus.DISABLED


@pytest.mark.asyncio
async def test_persistent_success_refreshes_credential_after_primary_auth() -> None:
    issuer = Issuer(
        PersistentCredentialIssued(
            credential=PERSISTENT,
            lifetime=LIFETIME,
        )
    )
    flow = _flow_class()(
        authenticate_backend_password=Authenticator(
            AuthenticationSucceeded(subject=SUBJECT, session_key=KEY)
        ),
        issue_persistent_credential=issuer,
    )

    result = await flow(request(RememberIntent.PERSIST))

    assert isinstance(result, BackendPasswordLoginSucceeded)
    assert result.persistent_disposition == RefreshPersistentCredential(
        credential=PERSISTENT,
        lifetime=LIFETIME,
    )
    assert result.persistence_status is BackendLoginPersistenceStatus.ISSUED
    assert issuer.calls == [SUBJECT]


@pytest.mark.asyncio
async def test_persistent_issue_failure_does_not_turn_login_into_failure() -> None:
    flow = _flow_class()(
        authenticate_backend_password=Authenticator(
            AuthenticationSucceeded(subject=SUBJECT, session_key=KEY)
        ),
        issue_persistent_credential=Issuer(
            PersistentCredentialIssueRejected(
                reason=PersistentCredentialIssueRejectReason.SUBJECT_DISABLED
            )
        ),
    )

    result = await flow(request(RememberIntent.PERSIST))

    assert isinstance(result, BackendPasswordLoginSucceeded)
    assert result.subject == SUBJECT
    assert result.session_disposition == IssueSessionCredential(
        session_id=KEY.session_id
    )
    assert isinstance(result.persistent_disposition, KeepPersistentCredential)
    assert result.persistence_status is BackendLoginPersistenceStatus.UNAVAILABLE


def test_backend_password_credentials_still_has_no_remember_field() -> None:
    assert "remember" not in BackendPasswordCredentials.model_fields
