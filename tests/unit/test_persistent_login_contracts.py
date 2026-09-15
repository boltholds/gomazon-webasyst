from datetime import timedelta

import pytest
from pydantic import TypeAdapter

from gomazon_webasyst.application.auth_values import AuthSessionKey, SessionId
from gomazon_webasyst.application.persistent_values import (
    PersistentCredential,
    PersistentCredentialLifetime,
)
from gomazon_webasyst.contracts.auth import AuthIdentity, AuthenticatedSubject
from gomazon_webasyst.contracts.enums import (
    BackendSessionEstablishmentKind,
    BackendSessionEstablishmentRejectReason,
    PersistentCredentialDispositionKind,
    PersistentCredentialIssueKind,
    PersistentCredentialIssueRejectReason,
    PersistentCredentialRejectReason,
    PersistentCredentialResolutionKind,
    PersistentLoginRejectReason,
    PersistentLoginResultKind,
    PersistentStrategyResultKind,
)
from gomazon_webasyst.contracts.persistent_login import (
    BackendSessionEstablished,
    BackendSessionEstablishmentRejected,
    BackendSessionEstablishmentResult,
    ClearPersistentCredential,
    KeepPersistentCredential,
    PersistentCredentialIssueRejected,
    PersistentCredentialIssueResult,
    PersistentCredentialIssued,
    PersistentCredentialRejected,
    PersistentCredentialResolution,
    PersistentCredentialResolved,
    PersistentLoginRejected,
    PersistentLoginResult,
    PersistentLoginRestored,
    PersistentStrategyNotApplicable,
    PersistentStrategyRejected,
    PersistentStrategyResolved,
    RefreshPersistentCredential,
)


IDENTITY = AuthIdentity(
    id=42,
    login="admin",
    password_hash="hash",
    is_user=1,
    create_datetime="2026-01-01T00:00:00",
)
SUBJECT = AuthenticatedSubject(id=42, login="admin")
SESSION_KEY = AuthSessionKey(contact_id=42, session_id=SessionId("session"))


def test_persistent_values_are_frozen_hashable():
    credential = PersistentCredential("abc")
    lifetime = PersistentCredentialLifetime(timedelta(days=30))

    assert {credential}
    assert {lifetime}

    with pytest.raises(AttributeError):
        credential.value = "changed"  # type: ignore[misc]


def test_disposition_variants_are_closed_and_string_serializable():
    refresh = RefreshPersistentCredential(
        credential=PersistentCredential("token"),
        lifetime=PersistentCredentialLifetime(timedelta(days=30)),
    )
    clear = ClearPersistentCredential()
    keep = KeepPersistentCredential()

    assert refresh.kind is PersistentCredentialDispositionKind.REFRESH
    assert clear.kind is PersistentCredentialDispositionKind.CLEAR
    assert keep.kind is PersistentCredentialDispositionKind.KEEP
    assert refresh.model_dump(mode="json")["kind"] == "refresh"


def test_strategy_and_resolution_results_are_explicit_variants():
    refresh = RefreshPersistentCredential(
        credential=PersistentCredential("token"),
        lifetime=PersistentCredentialLifetime(timedelta(days=30)),
    )

    strategy_ok = PersistentStrategyResolved(identity=IDENTITY, disposition=refresh)
    strategy_skip = PersistentStrategyNotApplicable()
    strategy_reject = PersistentStrategyRejected(
        reason=PersistentCredentialRejectReason.INVALID,
        disposition=ClearPersistentCredential(),
    )
    resolved = PersistentCredentialResolved(identity=IDENTITY, disposition=refresh)
    rejected = PersistentCredentialRejected(
        reason=PersistentCredentialRejectReason.UNSUPPORTED,
        disposition=ClearPersistentCredential(),
    )

    assert strategy_ok.kind is PersistentStrategyResultKind.RESOLVED
    assert strategy_skip.kind is PersistentStrategyResultKind.NOT_APPLICABLE
    assert strategy_reject.kind is PersistentStrategyResultKind.REJECTED
    assert resolved.kind is PersistentCredentialResolutionKind.RESOLVED
    assert rejected.kind is PersistentCredentialResolutionKind.REJECTED


def test_issue_and_session_establishment_results_are_explicit_variants():
    issued = PersistentCredentialIssued(
        credential=PersistentCredential("token"),
        lifetime=PersistentCredentialLifetime(timedelta(days=30)),
    )
    issue_rejected = PersistentCredentialIssueRejected(
        reason=PersistentCredentialIssueRejectReason.SUBJECT_DISABLED
    )
    established = BackendSessionEstablished(subject=SUBJECT, session_key=SESSION_KEY)
    establishment_rejected = BackendSessionEstablishmentRejected(
        reason=BackendSessionEstablishmentRejectReason.SESSION_UNAVAILABLE
    )

    assert issued.kind is PersistentCredentialIssueKind.ISSUED
    assert issue_rejected.kind is PersistentCredentialIssueKind.REJECTED
    assert established.kind is BackendSessionEstablishmentKind.ESTABLISHED
    assert establishment_rejected.kind is BackendSessionEstablishmentKind.REJECTED


def test_restore_result_is_discriminated_without_optional_fields():
    restored = PersistentLoginRestored(
        subject=SUBJECT,
        session_key=SESSION_KEY,
        credential_disposition=RefreshPersistentCredential(
            credential=PersistentCredential("token"),
            lifetime=PersistentCredentialLifetime(timedelta(days=30)),
        ),
    )
    rejected = PersistentLoginRejected(
        reason=PersistentLoginRejectReason.CREDENTIAL_REJECTED,
        credential_disposition=ClearPersistentCredential(),
    )

    assert restored.kind is PersistentLoginResultKind.RESTORED
    assert rejected.kind is PersistentLoginResultKind.REJECTED


def test_discriminated_unions_accept_raw_string_kinds():
    issue = TypeAdapter(PersistentCredentialIssueResult).validate_python(
        {
            "kind": "rejected",
            "reason": "subject_not_found",
        }
    )
    session = TypeAdapter(BackendSessionEstablishmentResult).validate_python(
        {
            "kind": "rejected",
            "reason": "session_unavailable",
        }
    )
    login = TypeAdapter(PersistentLoginResult).validate_python(
        {
            "kind": "rejected",
            "reason": "credential_rejected",
            "credential_disposition": {"kind": "clear"},
        }
    )
    resolution = TypeAdapter(PersistentCredentialResolution).validate_python(
        {
            "kind": "rejected",
            "reason": "malformed",
            "disposition": {"kind": "clear"},
        }
    )

    assert issue.reason is PersistentCredentialIssueRejectReason.SUBJECT_NOT_FOUND
    assert session.reason is BackendSessionEstablishmentRejectReason.SESSION_UNAVAILABLE
    assert login.reason is PersistentLoginRejectReason.CREDENTIAL_REJECTED
    assert resolution.reason is PersistentCredentialRejectReason.MALFORMED
