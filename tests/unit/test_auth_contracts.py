from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest
from pydantic import TypeAdapter, ValidationError

from gomazon_webasyst.application.auth_values import AuthSessionKey, SessionId
from gomazon_webasyst.contracts.auth import (
    AuthIdentity,
    AuthenticationRejected,
    AuthenticationResult,
    IdentityKey,
    IdentityLookupPlan,
    IdentityResolution,
    IdentityResolutionError,
    PasswordVerification,
    PasswordVerificationError,
    SessionResolutionError,
    SessionResolutionResult,
)
from gomazon_webasyst.contracts.enums import (
    AuthenticationRejectType,
    AuthenticationResultKind,
    IdentityResolutionErrorType,
    IdentityResolutionKind,
    PasswordVerificationErrorType,
    PasswordVerificationKind,
    SessionResolutionErrorType,
    SessionResolutionKind,
)


def test_session_value_objects_are_frozen_hashable_and_composable():
    session_id = SessionId("sess-123")
    key = AuthSessionKey(contact_id=42, session_id=session_id)

    assert key == AuthSessionKey(contact_id=42, session_id=SessionId("sess-123"))
    assert {key} == {AuthSessionKey(contact_id=42, session_id=SessionId("sess-123"))}

    with pytest.raises(FrozenInstanceError):
        session_id.value = "other"  # type: ignore[misc]


def test_identity_key_scheme_is_open_extension_identifier():
    key = IdentityKey(scheme="employee_id", value="EMP-42")
    plan = IdentityLookupPlan(keys=(key,))

    assert plan.keys == (key,)
    assert key.scheme == "employee_id"


def test_identity_resolution_uses_explicit_error_variant_not_none():
    adapter = TypeAdapter(IdentityResolution)
    result = adapter.validate_python({"kind": "error", "type": "not_found"})

    assert isinstance(result, IdentityResolutionError)
    assert result.kind is IdentityResolutionKind.ERROR
    assert result.type is IdentityResolutionErrorType.NOT_FOUND

    with pytest.raises(ValidationError):
        adapter.validate_python(None)


def test_password_verification_uses_explicit_error_variant_not_bool():
    adapter = TypeAdapter(PasswordVerification)
    result = adapter.validate_python({"kind": "error", "type": "invalid"})

    assert isinstance(result, PasswordVerificationError)
    assert result.kind is PasswordVerificationKind.ERROR
    assert result.type is PasswordVerificationErrorType.INVALID

    with pytest.raises(ValidationError):
        adapter.validate_python(False)


def test_authentication_result_and_session_result_serialize_enumstr_as_strings():
    auth_adapter = TypeAdapter(AuthenticationResult)
    auth_result = auth_adapter.validate_python(
        {"kind": "rejected", "type": "invalid_credentials"}
    )
    assert isinstance(auth_result, AuthenticationRejected)
    assert auth_result.kind is AuthenticationResultKind.REJECTED
    assert auth_result.type is AuthenticationRejectType.INVALID_CREDENTIALS
    assert auth_adapter.dump_python(auth_result, mode="json") == {
        "kind": "rejected",
        "type": "invalid_credentials",
    }

    session_adapter = TypeAdapter(SessionResolutionResult)
    session_result = session_adapter.validate_python(
        {"kind": "error", "type": "credentials_changed"}
    )
    assert isinstance(session_result, SessionResolutionError)
    assert session_result.kind is SessionResolutionKind.ERROR
    assert session_result.type is SessionResolutionErrorType.CREDENTIALS_CHANGED


def test_auth_identity_is_auth_projection_not_contact_shape():
    identity = AuthIdentity(
        id=7,
        login="admin",
        password_hash="legacy-hash",
        is_user=1,
        create_datetime=datetime(2026, 1, 2, 3, 4, 5),
    )

    assert identity.id == 7
    assert identity.password_hash == "legacy-hash"
    assert "company" not in AuthIdentity.model_fields
