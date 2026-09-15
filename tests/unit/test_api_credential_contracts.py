from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from typing import get_args

import pytest
from pydantic import TypeAdapter

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_credential_values import (
    ApiAccessToken,
    ApiClientId,
    ApiScope,
    AuthorizationCode,
)
from gomazon_webasyst.contracts.api_credentials import (
    ApiTokenExpiresAt,
    ApiTokenExpiry,
    ApiTokenLastUsedAt,
    ApiTokenNeverExpires,
    ApiTokenNeverUsed,
    ApiTokenResolved,
    ApiTokenResolution,
    StoredApiAccessToken,
    StoredAuthorizationCode,
)
from gomazon_webasyst.contracts.enums import ApiTokenExpiryKind, ApiTokenLastUseKind, ApiTokenLookupKind


def test_api_credential_values_are_frozen_hashable_and_non_empty() -> None:
    code = AuthorizationCode("a" * 32)
    token = ApiAccessToken("b" * 32)
    client = ApiClientId("client")

    assert {code, token, client}
    with pytest.raises(FrozenInstanceError):
        code.value = "c" * 32  # type: ignore[misc]

    for value_type in (AuthorizationCode, ApiAccessToken, ApiClientId):
        with pytest.raises(ValueError):
            value_type("")
        with pytest.raises(ValueError):
            value_type("   ")


def test_api_scope_is_non_empty_and_order_preserving_unique() -> None:
    scope = ApiScope((AppId("shop"), AppId("site"), AppId("shop")))

    assert scope.apps == (AppId("shop"), AppId("site"))
    assert hash(scope)

    with pytest.raises(ValueError):
        ApiScope(())


def test_api_scope_convenience_constructor_uses_typed_app_ids() -> None:
    scope = ApiScope.of("shop", "site", "shop")

    assert scope.apps == (AppId("shop"), AppId("site"))


def test_token_expiry_and_last_use_are_explicit_state_unions() -> None:
    at = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)

    never = TypeAdapter(ApiTokenExpiry).validate_python({"kind": "never"})
    expiring = TypeAdapter(ApiTokenExpiry).validate_python(
        {"kind": "expires_at", "at": at.isoformat()}
    )

    assert isinstance(never, ApiTokenNeverExpires)
    assert never.kind is ApiTokenExpiryKind.NEVER
    assert isinstance(expiring, ApiTokenExpiresAt)
    assert expiring.at == at

    never_used = ApiTokenNeverUsed()
    used = ApiTokenLastUsedAt(at=at)
    assert never_used.kind is ApiTokenLastUseKind.NEVER_USED
    assert used.kind is ApiTokenLastUseKind.LAST_USED_AT


def test_stored_records_use_typed_values_without_nullable_state() -> None:
    now = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
    code_record = StoredAuthorizationCode(
        code=AuthorizationCode("a" * 32),
        contact_id=42,
        client_id=ApiClientId("client"),
        scope=ApiScope.of("shop", "site"),
        expires_at=now,
    )
    token_record = StoredApiAccessToken(
        token=ApiAccessToken("b" * 32),
        contact_id=42,
        client_id=ApiClientId("client"),
        scope=ApiScope.of("shop"),
        created_at=now,
        last_use=ApiTokenNeverUsed(),
        expiry=ApiTokenNeverExpires(),
    )

    assert code_record.scope.apps == (AppId("shop"), AppId("site"))
    assert isinstance(token_record.expiry, ApiTokenNeverExpires)
    assert isinstance(token_record.last_use, ApiTokenNeverUsed)

    for model in (StoredAuthorizationCode, StoredApiAccessToken):
        for field in model.model_fields.values():
            assert type(None) not in get_args(field.annotation)


def test_repository_token_lookup_is_explicit_discriminated_result() -> None:
    now = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
    record = StoredApiAccessToken(
        token=ApiAccessToken("b" * 32),
        contact_id=42,
        client_id=ApiClientId("client"),
        scope=ApiScope.of("shop"),
        created_at=now,
        last_use=ApiTokenNeverUsed(),
        expiry=ApiTokenNeverExpires(),
    )

    resolved = ApiTokenResolved(record=record)
    parsed = TypeAdapter(ApiTokenResolution).validate_python(
        {"kind": "resolved", "record": record}
    )

    assert resolved.kind is ApiTokenLookupKind.RESOLVED
    assert isinstance(parsed, ApiTokenResolved)
