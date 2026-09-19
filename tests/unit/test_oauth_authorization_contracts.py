from dataclasses import FrozenInstanceError
from importlib import import_module
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
from gomazon_webasyst.contracts.auth import AuthenticatedSubject


def _module(name: str):
    try:
        return import_module(name)
    except ModuleNotFoundError as error:
        pytest.fail(f"missing oauth authorization module: {name}: {error}")


def test_consent_application_identity_is_app_id() -> None:
    entity = _module(
        "gomazon_webasyst.application.oauth_authorization.entities.consent_application"
    )
    client = _module(
        "gomazon_webasyst.application.oauth_authorization.vo.client"
    )
    app = entity.OAuthConsentApplication(
        app_id=AppId("shop"),
        display_name=client.OAuthAppDisplayName("Shop"),
        icon=client.OAuthAppIconReference("/wa-apps/shop/img/shop48.png"),
    )
    assert app.app_id == AppId("shop")
    with pytest.raises(FrozenInstanceError):
        app.app_id = AppId("crm")  # type: ignore[misc]


def test_requested_scope_preserves_order_and_deduplicates() -> None:
    auth = _module(
        "gomazon_webasyst.application.oauth_authorization.vo.authorization"
    )
    scope = auth.OAuthRequestedScope(
        (AppId("shop"), AppId("crm"), AppId("shop"))
    )
    assert scope.apps == (AppId("shop"), AppId("crm"))


def test_open_oauth_values_are_frozen_and_validate_non_empty() -> None:
    client = _module(
        "gomazon_webasyst.application.oauth_authorization.vo.client"
    )
    auth = _module(
        "gomazon_webasyst.application.oauth_authorization.vo.authorization"
    )

    values = (
        client.OAuthClientName("Desktop Client"),
        client.OAuthAppDisplayName("Shop"),
        client.OAuthAppIconReference("/icon.png"),
        auth.OAuthRedirectUri("https://client.example/callback"),
        auth.OAuthCsrfToken("csrf-token"),
    )
    assert len(set(values)) == len(values)

    for factory in (
        client.OAuthClientName,
        client.OAuthAppDisplayName,
        client.OAuthAppIconReference,
        auth.OAuthRedirectUri,
        auth.OAuthCsrfToken,
    ):
        with pytest.raises(ValueError):
            factory("")


def test_closed_oauth_domains_are_enumstr_and_parse_raw_strings() -> None:
    enums = import_module("gomazon_webasyst.contracts.enums")
    expected = (
        ("OAuthResponseType", "CODE", "code"),
        ("OAuthResponseType", "TOKEN", "token"),
        ("OAuthConsentDecision", "APPROVE", "approve"),
        ("OAuthConsentDecision", "DENY", "deny"),
        ("OAuthGrantType", "AUTHORIZATION_CODE", "authorization_code"),
        ("OAuthConsentAppLookupKind", "MISSING", "missing"),
        ("OAuthConsentAccessKind", "GRANTED", "granted"),
        ("OAuthRevokeTargetKind", "MISSING", "missing"),
        ("OAuthRevokeAuthenticationKind", "AUTHENTICATED", "authenticated"),
    )
    for enum_name, member_name, raw in expected:
        enum_type = getattr(enums, enum_name)
        assert issubclass(enum_type, enums.EnumStr)
        assert enum_type(raw) is getattr(enum_type, member_name)


def test_authorization_request_uses_explicit_redirect_state() -> None:
    enums = import_module("gomazon_webasyst.contracts.enums")
    client = _module(
        "gomazon_webasyst.application.oauth_authorization.vo.client"
    )
    auth = _module(
        "gomazon_webasyst.application.oauth_authorization.vo.authorization"
    )
    requests = _module(
        "gomazon_webasyst.application.oauth_authorization.composites.requests"
    )

    request = requests.OAuthAuthorizationRequest(
        client_id=ApiClientId("client"),
        client_name=client.OAuthClientName("Client"),
        response_type=enums.OAuthResponseType.CODE,
        requested_scope=auth.OAuthRequestedScope((AppId("shop"),)),
        redirect_target=auth.OAuthRedirectMissing(),
    )
    assert isinstance(request.redirect_target, auth.OAuthRedirectMissing)
    with pytest.raises(FrozenInstanceError):
        request.client_id = ApiClientId("other")  # type: ignore[misc]


def test_authenticated_decision_request_keeps_subject_and_decision_typed() -> None:
    enums = import_module("gomazon_webasyst.contracts.enums")
    client = _module(
        "gomazon_webasyst.application.oauth_authorization.vo.client"
    )
    auth = _module(
        "gomazon_webasyst.application.oauth_authorization.vo.authorization"
    )
    requests = _module(
        "gomazon_webasyst.application.oauth_authorization.composites.requests"
    )
    subject = AuthenticatedSubject(id=42, login="admin")
    authorization = requests.OAuthAuthorizationRequest(
        client_id=ApiClientId("client"),
        client_name=client.OAuthClientName("Client"),
        response_type=enums.OAuthResponseType.CODE,
        requested_scope=auth.OAuthRequestedScope((AppId("shop"),)),
        redirect_target=auth.OAuthRedirectMissing(),
    )
    decision = requests.OAuthAuthenticatedDecisionRequest(
        subject=subject,
        authorization_request=authorization,
        decision=enums.OAuthConsentDecision.APPROVE,
    )
    assert decision.subject == subject
    assert decision.decision is enums.OAuthConsentDecision.APPROVE


def test_oauth_result_union_accepts_raw_discriminator_and_serializes_string() -> None:
    contracts = _module("gomazon_webasyst.contracts.oauth_authorization")
    adapter = TypeAdapter(contracts.OAuthAuthorizationResult)

    invalid = adapter.validate_python({"kind": "invalid_scope"})
    assert isinstance(invalid, contracts.OAuthAuthorizationInvalidScope)
    assert adapter.dump_python(invalid, mode="json") == {"kind": "invalid_scope"}

    unavailable = adapter.validate_python({"kind": "grant_unavailable"})
    assert isinstance(unavailable, contracts.OAuthAuthorizationGrantUnavailable)
    assert adapter.dump_python(unavailable, mode="json") == {
        "kind": "grant_unavailable"
    }


def test_oauth_result_models_are_frozen_and_do_not_use_none_fields() -> None:
    contracts = _module("gomazon_webasyst.contracts.oauth_authorization")
    model_types = (
        contracts.OAuthConsentRequired,
        contracts.OAuthAuthorizationCodeGranted,
        contracts.OAuthImplicitTokenGranted,
        contracts.OAuthAuthorizationDenied,
        contracts.OAuthAuthorizationInvalidScope,
        contracts.OAuthAuthorizationGrantUnavailable,
    )
    for model_type in model_types:
        assert model_type.model_config.get("frozen") is True
        for field in model_type.model_fields.values():
            assert type(None) not in get_args(field.annotation)


def test_revoke_target_is_explicit_value_variant() -> None:
    revoke = _module(
        "gomazon_webasyst.application.oauth_authorization.vo.revoke"
    )
    provided = revoke.RevokeTargetProvided(ApiAccessToken("a" * 32))
    missing = revoke.RevokeTargetMissing()
    assert provided.token == ApiAccessToken("a" * 32)
    assert provided != missing
