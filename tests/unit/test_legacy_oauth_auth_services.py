from importlib import import_module

import pytest

from gomazon_webasyst.application.api_execution.vo.parameters import ApiParameterMap
from gomazon_webasyst.application.oauth_authorization.composites.requests import (
    OAuthAuthorizationRequest,
)
from gomazon_webasyst.application.oauth_authorization.vo.authorization import (
    OAuthRedirectMissing,
    OAuthRedirectProvided,
    OAuthRedirectUri,
    OAuthRequestedScope,
)
from gomazon_webasyst.application.oauth_authorization.vo.client import OAuthClientName
from gomazon_webasyst.application.api_credential_values import ApiClientId
from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.contracts.enums import OAuthResponseType


def _module(name):
    try:
        return import_module(name)
    except ModuleNotFoundError as error:
        pytest.fail(f"legacy oauth compatibility module missing: {name}: {error}")


def test_legacy_redirect_policy_accepts_provided_and_missing_redirects() -> None:
    policy = _module(
        "gomazon_webasyst.compatibility.webasyst.oauth.services.redirects"
    ).LegacyUnregisteredRedirectPolicy()
    ports = _module("gomazon_webasyst.application.ports.oauth_redirect_policy")

    assert isinstance(
        policy.validate(
            ApiClientId("client"),
            OAuthRedirectProvided(OAuthRedirectUri("https://client/cb")),
        ),
        ports.OAuthRedirectAccepted,
    )
    assert isinstance(
        policy.validate(ApiClientId("client"), OAuthRedirectMissing()),
        ports.OAuthRedirectAccepted,
    )


def test_cancel_token_redirects_even_with_empty_redirect() -> None:
    transport = _module(
        "gomazon_webasyst.compatibility.webasyst.oauth.vo.transport"
    )
    cancel = _module(
        "gomazon_webasyst.compatibility.webasyst.oauth.services.cancel"
    )
    result = cancel.LegacyOAuthCancelService().cancel(
        transport.LegacyOAuthCancelRequest(
            raw_response_type="token",
            raw_redirect_uri="",
            raw_client_name="Client",
        )
    )
    assert isinstance(result, cancel.OAuthCancelRedirect)
    assert result.location == "#error=access_denied"


@pytest.mark.parametrize("response_type", ["", "code", "unknown"])
def test_cancel_code_style_without_redirect_is_framework_403(response_type) -> None:
    transport = _module(
        "gomazon_webasyst.compatibility.webasyst.oauth.vo.transport"
    )
    cancel = _module(
        "gomazon_webasyst.compatibility.webasyst.oauth.services.cancel"
    )
    result = cancel.LegacyOAuthCancelService().cancel(
        transport.LegacyOAuthCancelRequest(
            raw_response_type=response_type,
            raw_redirect_uri="",
            raw_client_name="Client",
        )
    )
    assert isinstance(result, cancel.OAuthCancelFrameworkError)
    assert result.error.http_status == 403
    assert result.error.code.value == "access_denied"


@pytest.mark.parametrize("response_type", ["", "code", "unknown"])
def test_cancel_code_style_with_redirect_uses_query(response_type) -> None:
    transport = _module(
        "gomazon_webasyst.compatibility.webasyst.oauth.vo.transport"
    )
    cancel = _module(
        "gomazon_webasyst.compatibility.webasyst.oauth.services.cancel"
    )
    result = cancel.LegacyOAuthCancelService().cancel(
        transport.LegacyOAuthCancelRequest(
            raw_response_type=response_type,
            raw_redirect_uri="https://client/cb",
            raw_client_name="Client",
        )
    )
    assert isinstance(result, cancel.OAuthCancelRedirect)
    assert result.location == "https://client/cb?error=access_denied"


def test_csrf_issue_reuses_existing_cookie_and_generates_when_missing() -> None:
    csrf = _module(
        "gomazon_webasyst.compatibility.webasyst.oauth.services.csrf"
    )
    service = csrf.LegacyOAuthCsrfService(generator=lambda: "generated")
    missing = service.issue(csrf.OAuthCsrfCookieMissing())
    existing = service.issue(csrf.OAuthCsrfCookieProvided("existing"))

    assert missing.token.value == "generated"
    assert missing.set_cookie is True
    assert existing.token.value == "existing"
    assert existing.set_cookie is False


@pytest.mark.parametrize(
    ("cookie", "form", "accepted"),
    [
        ("same", "same", True),
        ("same", "other", False),
        ("", "same", False),
        ("same", "", False),
        ("0", "0", False),
    ],
)
def test_csrf_double_submit_validation(cookie, form, accepted) -> None:
    csrf = _module(
        "gomazon_webasyst.compatibility.webasyst.oauth.services.csrf"
    )
    service = csrf.LegacyOAuthCsrfService(generator=lambda: "unused")
    cookie_state = (
        csrf.OAuthCsrfCookieProvided(cookie)
        if cookie
        else csrf.OAuthCsrfCookieMissing()
    )
    form_state = (
        csrf.OAuthCsrfFormProvided(form)
        if form
        else csrf.OAuthCsrfFormMissing()
    )
    result = service.validate(cookie_state, form_state)
    assert isinstance(
        result,
        csrf.OAuthCsrfAccepted if accepted else csrf.OAuthCsrfRejected,
    )


def _request(response_type, redirect):
    return OAuthAuthorizationRequest(
        client_id=ApiClientId("client"),
        client_name=OAuthClientName("Client"),
        response_type=response_type,
        requested_scope=OAuthRequestedScope((AppId("shop"),)),
        redirect_target=redirect,
    )


def test_authenticated_code_deny_without_redirect_is_html_error_not_framework_403() -> None:
    deny = _module(
        "gomazon_webasyst.compatibility.webasyst.oauth.services.deny"
    )
    result = deny.LegacyOAuthDenyService().deny(
        _request(OAuthResponseType.CODE, OAuthRedirectMissing())
    )
    assert isinstance(result, deny.OAuthDenyHtmlError)
    assert result.error_code == "access_denied"


def test_authenticated_deny_redirects_code_query_and_token_fragment() -> None:
    deny = _module(
        "gomazon_webasyst.compatibility.webasyst.oauth.services.deny"
    )
    provided = OAuthRedirectProvided(OAuthRedirectUri("https://client/cb"))

    code = deny.LegacyOAuthDenyService().deny(
        _request(OAuthResponseType.CODE, provided)
    )
    token = deny.LegacyOAuthDenyService().deny(
        _request(OAuthResponseType.TOKEN, provided)
    )
    assert code.location == "https://client/cb?error=access_denied"
    assert token.location == "https://client/cb#error=access_denied"
