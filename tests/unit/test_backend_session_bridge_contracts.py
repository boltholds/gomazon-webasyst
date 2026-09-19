from dataclasses import FrozenInstanceError
import json

import pytest
from pydantic import TypeAdapter

from gomazon_webasyst.application.auth_values import SessionId
from gomazon_webasyst.application.backend_session_bridge.composites.requests import (
    BackendCurrentSubjectRequest,
    BackendLogoutRequest,
)
from gomazon_webasyst.application.backend_session_bridge.vo.credentials import (
    PersistentCredentialMissing,
    SessionCredentialMalformed,
    SessionCredentialMissing,
    SessionCredentialProvided,
)
from gomazon_webasyst.application.persistent_values import PersistentCredential
from gomazon_webasyst.contracts.auth import SessionMetadata
from gomazon_webasyst.contracts.backend_session_bridge import (
    ClearSessionCredential,
    IssueSessionCredential,
    KeepSessionCredential,
    SessionCredentialDisposition,
)
from gomazon_webasyst.contracts.enums import (
    BackendLoginPersistenceStatus,
    BackendLogoutKind,
    BackendPasswordLoginKind,
    CurrentBackendSubjectKind,
    CurrentBackendSubjectReason,
    EnumStr,
    PersistentLoginMode,
    RememberIntent,
    SessionCredentialDispositionKind,
)


def test_bridge_credential_states_are_explicit_frozen_values() -> None:
    provided = SessionCredentialProvided(SessionId("sess-1"))
    assert provided.session_id == SessionId("sess-1")
    assert SessionCredentialMissing() != SessionCredentialMalformed()
    assert PersistentCredentialMissing() != PersistentCredential("credential")
    with pytest.raises(FrozenInstanceError):
        provided.session_id = SessionId("other")  # type: ignore[misc]


def test_remember_and_bridge_status_domains_are_enumstr() -> None:
    enum_types = (
        RememberIntent,
        PersistentLoginMode,
        SessionCredentialDispositionKind,
        CurrentBackendSubjectKind,
        CurrentBackendSubjectReason,
        BackendPasswordLoginKind,
        BackendLoginPersistenceStatus,
        BackendLogoutKind,
    )
    for enum_type in enum_types:
        assert issubclass(enum_type, EnumStr)

    assert RememberIntent.PERSIST.value == "persist"
    assert PersistentLoginMode.DISABLED.value == "disabled"


def test_session_disposition_accepts_raw_discriminator_and_serializes_string() -> None:
    adapter = TypeAdapter(SessionCredentialDisposition)
    value = adapter.validate_python(
        {
            "kind": "issue",
            "session_id": SessionId("sess-1"),
        }
    )
    assert isinstance(value, IssueSessionCredential)
    assert value.session_id == SessionId("sess-1")
    payload = json.loads(adapter.dump_json(value))
    assert payload["kind"] == "issue"

    assert isinstance(
        adapter.validate_python({"kind": "clear"}),
        ClearSessionCredential,
    )
    assert isinstance(
        adapter.validate_python({"kind": "keep"}),
        KeepSessionCredential,
    )


def test_bridge_request_composites_preserve_explicit_credential_states() -> None:
    current = BackendCurrentSubjectRequest(
        session_credential=SessionCredentialMissing(),
        persistent_credential=PersistentCredentialMissing(),
        session_metadata=SessionMetadata(user_agent="pytest"),
        persistent_login_mode=PersistentLoginMode.DISABLED,
    )
    logout = BackendLogoutRequest(
        session_credential=SessionCredentialMalformed(),
    )

    assert isinstance(current.session_credential, SessionCredentialMissing)
    assert current.persistent_login_mode is PersistentLoginMode.DISABLED
    assert isinstance(logout.session_credential, SessionCredentialMalformed)
