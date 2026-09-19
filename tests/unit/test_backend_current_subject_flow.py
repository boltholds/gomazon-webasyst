from importlib import import_module

import pytest

from gomazon_webasyst.application.auth_values import AuthSessionKey, SessionId
from gomazon_webasyst.application.backend_session_bridge.composites.requests import (
    BackendCurrentSubjectRequest,
)
from gomazon_webasyst.application.backend_session_bridge.vo.credentials import (
    PersistentCredentialMissing,
    PersistentCredentialProvided,
    SessionCredentialMalformed,
    SessionCredentialMissing,
    SessionCredentialProvided,
)
from gomazon_webasyst.application.persistent_values import PersistentCredential
from gomazon_webasyst.contracts.auth import (
    AuthenticatedSubject,
    SessionMetadata,
    SessionResolutionError,
    SessionResolved,
)
from gomazon_webasyst.contracts.backend_session_bridge import (
    ClearSessionCredential,
    CurrentBackendSubjectResolved,
    CurrentBackendSubjectUnauthenticated,
    IssueSessionCredential,
    KeepSessionCredential,
)
from gomazon_webasyst.contracts.enums import (
    CurrentBackendSubjectReason,
    PersistentLoginMode,
    PersistentLoginRejectReason,
    SessionResolutionErrorType,
)
from gomazon_webasyst.contracts.persistent_login import (
    ClearPersistentCredential,
    KeepPersistentCredential,
    PersistentLoginRejected,
    PersistentLoginRestored,
    RefreshPersistentCredential,
)
from gomazon_webasyst.application.persistent_values import PersistentCredentialLifetime
from datetime import timedelta


SUBJECT = AuthenticatedSubject(id=42, login="admin")
KEY = AuthSessionKey(contact_id=42, session_id=SessionId("sess-1"))
NEW_KEY = AuthSessionKey(contact_id=42, session_id=SessionId("sess-new"))
CREDENTIAL = PersistentCredential("credential")
REFRESH = RefreshPersistentCredential(
    credential=CREDENTIAL,
    lifetime=PersistentCredentialLifetime(timedelta(days=30)),
)


def _flow_class():
    try:
        return import_module(
            "gomazon_webasyst.application.backend_session_bridge.composites.current_subject"
        ).BackendCurrentSubjectFlow
    except (ModuleNotFoundError, AttributeError) as error:
        pytest.fail(f"current subject flow missing: {error}")


class SessionResolver:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def __call__(self, session_id):
        self.calls.append(session_id)
        return self.result


class PersistentRestore:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def __call__(self, request):
        self.calls.append(request)
        return self.result


class FailIfCalled:
    async def __call__(self, request):
        raise AssertionError("persistent restore must not be called")


def request(session, persistent, *, mode=PersistentLoginMode.ENABLED):
    return BackendCurrentSubjectRequest(
        session_credential=session,
        persistent_credential=persistent,
        session_metadata=SessionMetadata(user_agent="pytest"),
        persistent_login_mode=mode,
    )


@pytest.mark.asyncio
async def test_valid_session_wins_and_persistent_restore_is_not_called() -> None:
    resolver = SessionResolver(SessionResolved(subject=SUBJECT, session_key=KEY))
    flow = _flow_class()(
        resolve_backend_session=resolver,
        restore_backend_session_from_persistent_credential=FailIfCalled(),
    )

    result = await flow(
        request(
            SessionCredentialProvided(KEY.session_id),
            PersistentCredentialProvided(CREDENTIAL),
        )
    )

    assert isinstance(result, CurrentBackendSubjectResolved)
    assert result.subject == SUBJECT
    assert isinstance(result.session_disposition, KeepSessionCredential)
    assert isinstance(result.persistent_disposition, KeepPersistentCredential)
    assert resolver.calls == [KEY.session_id]


@pytest.mark.asyncio
async def test_rejected_session_falls_back_to_persistent_and_issues_new_session() -> None:
    restore = PersistentRestore(
        PersistentLoginRestored(
            subject=SUBJECT,
            session_key=NEW_KEY,
            credential_disposition=REFRESH,
        )
    )
    flow = _flow_class()(
        resolve_backend_session=SessionResolver(
            SessionResolutionError(type=SessionResolutionErrorType.EXPIRED)
        ),
        restore_backend_session_from_persistent_credential=restore,
    )

    result = await flow(
        request(
            SessionCredentialProvided(SessionId("sess-old")),
            PersistentCredentialProvided(CREDENTIAL),
        )
    )

    assert isinstance(result, CurrentBackendSubjectResolved)
    assert result.session_disposition == IssueSessionCredential(
        session_id=NEW_KEY.session_id
    )
    assert result.persistent_disposition == REFRESH
    assert restore.calls[0].credential == CREDENTIAL


@pytest.mark.asyncio
async def test_malformed_session_can_restore_from_persistent_credential() -> None:
    flow = _flow_class()(
        resolve_backend_session=SessionResolver(
            SessionResolutionError(type=SessionResolutionErrorType.NOT_FOUND)
        ),
        restore_backend_session_from_persistent_credential=PersistentRestore(
            PersistentLoginRestored(
                subject=SUBJECT,
                session_key=NEW_KEY,
                credential_disposition=REFRESH,
            )
        ),
    )

    result = await flow(
        request(
            SessionCredentialMalformed(),
            PersistentCredentialProvided(CREDENTIAL),
        )
    )

    assert isinstance(result, CurrentBackendSubjectResolved)
    assert result.session_disposition == IssueSessionCredential(
        session_id=NEW_KEY.session_id
    )


@pytest.mark.asyncio
async def test_persistent_login_disabled_never_restores_or_clears_persistent_transport() -> None:
    flow = _flow_class()(
        resolve_backend_session=SessionResolver(
            SessionResolutionError(type=SessionResolutionErrorType.EXPIRED)
        ),
        restore_backend_session_from_persistent_credential=FailIfCalled(),
    )

    result = await flow(
        request(
            SessionCredentialProvided(SessionId("stale")),
            PersistentCredentialProvided(CREDENTIAL),
            mode=PersistentLoginMode.DISABLED,
        )
    )

    assert isinstance(result, CurrentBackendSubjectUnauthenticated)
    assert result.reason is CurrentBackendSubjectReason.SESSION_REJECTED
    assert isinstance(result.session_disposition, ClearSessionCredential)
    assert isinstance(result.persistent_disposition, KeepPersistentCredential)


@pytest.mark.asyncio
async def test_missing_credentials_are_explicit_unauthenticated_state() -> None:
    flow = _flow_class()(
        resolve_backend_session=SessionResolver(
            SessionResolutionError(type=SessionResolutionErrorType.NOT_FOUND)
        ),
        restore_backend_session_from_persistent_credential=FailIfCalled(),
    )

    result = await flow(
        request(SessionCredentialMissing(), PersistentCredentialMissing())
    )

    assert isinstance(result, CurrentBackendSubjectUnauthenticated)
    assert result.reason is CurrentBackendSubjectReason.NO_CREDENTIAL
    assert isinstance(result.session_disposition, KeepSessionCredential)
    assert isinstance(result.persistent_disposition, KeepPersistentCredential)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("persistent_result", "reason", "persistent_type"),
    [
        (
            PersistentLoginRejected(
                reason=PersistentLoginRejectReason.CREDENTIAL_REJECTED,
                credential_disposition=ClearPersistentCredential(),
            ),
            CurrentBackendSubjectReason.PERSISTENT_REJECTED,
            ClearPersistentCredential,
        ),
        (
            PersistentLoginRejected(
                reason=PersistentLoginRejectReason.SESSION_UNAVAILABLE,
                credential_disposition=KeepPersistentCredential(),
            ),
            CurrentBackendSubjectReason.SESSION_UNAVAILABLE,
            KeepPersistentCredential,
        ),
    ],
)
async def test_persistent_rejection_preserves_disposition(
    persistent_result,
    reason,
    persistent_type,
) -> None:
    flow = _flow_class()(
        resolve_backend_session=SessionResolver(
            SessionResolutionError(type=SessionResolutionErrorType.EXPIRED)
        ),
        restore_backend_session_from_persistent_credential=PersistentRestore(
            persistent_result
        ),
    )

    result = await flow(
        request(
            SessionCredentialProvided(SessionId("stale")),
            PersistentCredentialProvided(CREDENTIAL),
        )
    )

    assert isinstance(result, CurrentBackendSubjectUnauthenticated)
    assert result.reason is reason
    assert isinstance(result.session_disposition, ClearSessionCredential)
    assert isinstance(result.persistent_disposition, persistent_type)


@pytest.mark.asyncio
async def test_infrastructure_failure_propagates() -> None:
    class BrokenResolver:
        async def __call__(self, session_id):
            raise RuntimeError("backend down")

    flow = _flow_class()(
        resolve_backend_session=BrokenResolver(),
        restore_backend_session_from_persistent_credential=FailIfCalled(),
    )

    with pytest.raises(RuntimeError, match="backend down"):
        await flow(
            request(
                SessionCredentialProvided(SessionId("sess")),
                PersistentCredentialMissing(),
            )
        )
