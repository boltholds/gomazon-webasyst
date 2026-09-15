from datetime import datetime, timedelta

import pytest

from gomazon_webasyst.application.auth_values import AuthSessionKey, SessionId
from gomazon_webasyst.application.persistent_login import (
    IssuePersistentCredential,
    RestoreBackendSessionFromPersistentCredential,
)
from gomazon_webasyst.application.persistent_values import (
    PersistentCredential,
    PersistentCredentialLifetime,
)
from gomazon_webasyst.contracts.auth import (
    AuthIdentity,
    AuthenticatedSubject,
    SessionMetadata,
    SubjectResolved,
    SubjectResolutionError,
)
from gomazon_webasyst.contracts.enums import (
    BackendSessionEstablishmentRejectReason,
    PersistentCredentialIssueRejectReason,
    PersistentCredentialRejectReason,
    PersistentLoginRejectReason,
    SubjectResolutionErrorType,
)
from gomazon_webasyst.contracts.persistent_login import (
    BackendSessionEstablished,
    BackendSessionEstablishmentRejected,
    ClearPersistentCredential,
    KeepPersistentCredential,
    PersistentCredentialIssueRejected,
    PersistentCredentialIssued,
    PersistentCredentialRejected,
    PersistentCredentialResolved,
    PersistentLoginRejected,
    PersistentLoginRequest,
    PersistentLoginRestored,
    RefreshPersistentCredential,
)


IDENTITY = AuthIdentity(
    id=42,
    login="admin",
    password_hash="hash",
    is_user=1,
    create_datetime=datetime(2026, 1, 1),
)
SUBJECT = AuthenticatedSubject(id=42, login="admin")
CREDENTIAL = PersistentCredential("credential")
LIFETIME = PersistentCredentialLifetime(timedelta(days=30))
KEY = AuthSessionKey(contact_id=42, session_id=SessionId("sess-1"))
REFRESH = RefreshPersistentCredential(credential=CREDENTIAL, lifetime=LIFETIME)


class SubjectStore:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def get(self, subject_id):
        self.calls.append(subject_id)
        return self.result


class Issuer:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def issue(self, identity):
        self.calls.append(identity)
        return self.result


class Resolver:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def resolve(self, credential):
        self.calls.append(credential)
        return self.result


class Establisher:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def establish(self, identity, metadata):
        self.calls.append((identity, metadata))
        return self.result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("subject_result", "reason"),
    [
        (
            SubjectResolutionError(type=SubjectResolutionErrorType.NOT_FOUND),
            PersistentCredentialIssueRejectReason.SUBJECT_NOT_FOUND,
        ),
        (
            SubjectResolutionError(type=SubjectResolutionErrorType.DISABLED),
            PersistentCredentialIssueRejectReason.SUBJECT_DISABLED,
        ),
    ],
)
async def test_issue_maps_subject_errors_to_explicit_rejection(subject_result, reason):
    issuer = Issuer(PersistentCredentialIssued(credential=CREDENTIAL, lifetime=LIFETIME))
    use_case = IssuePersistentCredential(
        subject_store=SubjectStore(subject_result),
        issuer=issuer,
    )

    result = await use_case(SUBJECT)

    assert isinstance(result, PersistentCredentialIssueRejected)
    assert result.reason is reason
    assert issuer.calls == []


@pytest.mark.asyncio
async def test_issue_delegates_to_configured_issuer_after_subject_resolution():
    issued = PersistentCredentialIssued(credential=CREDENTIAL, lifetime=LIFETIME)
    issuer = Issuer(issued)
    use_case = IssuePersistentCredential(
        subject_store=SubjectStore(SubjectResolved(identity=IDENTITY)),
        issuer=issuer,
    )

    result = await use_case(SUBJECT)

    assert result == issued
    assert issuer.calls == [IDENTITY]


@pytest.mark.asyncio
async def test_restore_rejected_credential_preserves_clear_disposition():
    resolver = Resolver(
        PersistentCredentialRejected(
            reason=PersistentCredentialRejectReason.INVALID,
            disposition=ClearPersistentCredential(),
        )
    )
    establisher = Establisher(
        BackendSessionEstablished(subject=SUBJECT, session_key=KEY)
    )
    use_case = RestoreBackendSessionFromPersistentCredential(
        resolver=resolver,
        session_establisher=establisher,
    )

    result = await use_case(PersistentLoginRequest(credential=CREDENTIAL))

    assert isinstance(result, PersistentLoginRejected)
    assert result.reason is PersistentLoginRejectReason.CREDENTIAL_REJECTED
    assert isinstance(result.credential_disposition, ClearPersistentCredential)
    assert establisher.calls == []


@pytest.mark.asyncio
async def test_restore_valid_credential_and_session_success_returns_refresh():
    resolver = Resolver(PersistentCredentialResolved(identity=IDENTITY, disposition=REFRESH))
    establisher = Establisher(
        BackendSessionEstablished(subject=SUBJECT, session_key=KEY)
    )
    use_case = RestoreBackendSessionFromPersistentCredential(
        resolver=resolver,
        session_establisher=establisher,
    )
    request = PersistentLoginRequest(
        credential=CREDENTIAL,
        session_metadata=SessionMetadata(user_agent="pytest"),
    )

    result = await use_case(request)

    assert isinstance(result, PersistentLoginRestored)
    assert result.session_key == KEY
    assert result.credential_disposition == REFRESH
    assert establisher.calls == [(IDENTITY, request.session_metadata)]


@pytest.mark.asyncio
async def test_restore_valid_credential_but_session_unavailable_keeps_credential():
    resolver = Resolver(PersistentCredentialResolved(identity=IDENTITY, disposition=REFRESH))
    establisher = Establisher(
        BackendSessionEstablishmentRejected(
            reason=BackendSessionEstablishmentRejectReason.SESSION_UNAVAILABLE
        )
    )
    use_case = RestoreBackendSessionFromPersistentCredential(
        resolver=resolver,
        session_establisher=establisher,
    )

    result = await use_case(PersistentLoginRequest(credential=CREDENTIAL))

    assert isinstance(result, PersistentLoginRejected)
    assert result.reason is PersistentLoginRejectReason.SESSION_UNAVAILABLE
    assert isinstance(result.credential_disposition, KeepPersistentCredential)
