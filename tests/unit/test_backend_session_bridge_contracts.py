from dataclasses import FrozenInstanceError
from importlib import import_module
import json

import pytest
from pydantic import TypeAdapter

from gomazon_webasyst.application.auth_values import SessionId
from gomazon_webasyst.application.persistent_values import PersistentCredential
from gomazon_webasyst.contracts.auth import SessionMetadata


def _bridge_module(name: str):
    try:
        return import_module(name)
    except ModuleNotFoundError as error:
        pytest.fail(f"missing bridge module: {name}: {error}")


def test_bridge_credential_states_are_explicit_frozen_values() -> None:
    module = _bridge_module(
        "gomazon_webasyst.application.backend_session_bridge.vo.credentials"
    )
    provided = module.SessionCredentialProvided(SessionId("sess-1"))
    assert provided.session_id == SessionId("sess-1")
    assert module.SessionCredentialMissing() != module.SessionCredentialMalformed()
    assert module.PersistentCredentialMissing() != PersistentCredential("credential")
    with pytest.raises(FrozenInstanceError):
        provided.session_id = SessionId("other")  # type: ignore[misc]


def test_remember_and_bridge_status_domains_are_enumstr() -> None:
    enums = import_module("gomazon_webasyst.contracts.enums")
    expected = (
        "RememberIntent",
        "PersistentLoginMode",
        "SessionCredentialDispositionKind",
        "CurrentBackendSubjectKind",
        "CurrentBackendSubjectReason",
        "BackendPasswordLoginKind",
        "BackendLoginPersistenceStatus",
        "BackendLogoutKind",
    )
    for name in expected:
        assert hasattr(enums, name), f"missing EnumStr domain: {name}"
        assert issubclass(getattr(enums, name), enums.EnumStr)

    assert enums.RememberIntent.PERSIST.value == "persist"
    assert enums.PersistentLoginMode.DISABLED.value == "disabled"


def test_session_disposition_accepts_raw_discriminator_and_serializes_string() -> None:
    contracts = _bridge_module("gomazon_webasyst.contracts.backend_session_bridge")
    adapter = TypeAdapter(contracts.SessionCredentialDisposition)
    value = adapter.validate_python(
        {
            "kind": "issue",
            "session_id": SessionId("sess-1"),
        }
    )
    assert isinstance(value, contracts.IssueSessionCredential)
    assert value.session_id == SessionId("sess-1")
    payload = json.loads(adapter.dump_json(value))
    assert payload["kind"] == "issue"

    assert isinstance(
        adapter.validate_python({"kind": "clear"}),
        contracts.ClearSessionCredential,
    )
    assert isinstance(
        adapter.validate_python({"kind": "keep"}),
        contracts.KeepSessionCredential,
    )


def test_bridge_request_composites_preserve_explicit_credential_states() -> None:
    requests = _bridge_module(
        "gomazon_webasyst.application.backend_session_bridge.composites.requests"
    )
    credentials = _bridge_module(
        "gomazon_webasyst.application.backend_session_bridge.vo.credentials"
    )
    enums = import_module("gomazon_webasyst.contracts.enums")

    current = requests.BackendCurrentSubjectRequest(
        session_credential=credentials.SessionCredentialMissing(),
        persistent_credential=credentials.PersistentCredentialMissing(),
        session_metadata=SessionMetadata(user_agent="pytest"),
        persistent_login_mode=enums.PersistentLoginMode.DISABLED,
    )
    logout = requests.BackendLogoutRequest(
        session_credential=credentials.SessionCredentialMalformed(),
    )

    assert isinstance(current.session_credential, credentials.SessionCredentialMissing)
    assert current.persistent_login_mode is enums.PersistentLoginMode.DISABLED
    assert isinstance(logout.session_credential, credentials.SessionCredentialMalformed)
