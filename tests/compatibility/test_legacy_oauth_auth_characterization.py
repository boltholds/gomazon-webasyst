import pytest

from gomazon_webasyst.application.api_execution.vo.parameters import ApiParameterMap
from gomazon_webasyst.application.api_credential_values import AuthorizationCode
from gomazon_webasyst.contracts.enums import OAuthResponseType


def _modules():
    try:
        from gomazon_webasyst.compatibility.webasyst.oauth.services.request_validation import (
            LegacyOAuthAuthorizationRequestService,
            OAuthAuthorizationRequestParsed,
            OAuthAuthorizationRequestRejected,
        )
        from gomazon_webasyst.compatibility.webasyst.oauth.services.redirects import (
            LegacyOAuthRedirectService,
        )
        return (
            LegacyOAuthAuthorizationRequestService,
            OAuthAuthorizationRequestParsed,
            OAuthAuthorizationRequestRejected,
            LegacyOAuthRedirectService,
        )
    except ModuleNotFoundError as error:
        pytest.fail(f"legacy oauth authorization services missing: {error}")


def query(**values):
    return ApiParameterMap(values)


@pytest.mark.parametrize("name", ["client_id", "client_name", "response_type", "scope"])
@pytest.mark.parametrize("value", ["", "0", 0, False])
def test_required_authorization_query_fields_use_php_falsy_semantics(
    name,
    value,
) -> None:
    Service, _, Rejected, _ = _modules()
    values = {
        "client_id": "client",
        "client_name": "Client",
        "response_type": "code",
        "scope": "shop",
    }
    values[name] = value
    result = Service().parse(query(**values))
    assert isinstance(result, Rejected)


def test_code_request_allows_missing_redirect_and_dedupes_scope() -> None:
    Service, Parsed, _, _ = _modules()
    result = Service().parse(
        query(
            client_id="client",
            client_name="Client",
            response_type="code",
            scope="shop,,crm,shop",
        )
    )
    assert isinstance(result, Parsed)
    assert result.request.response_type is OAuthResponseType.CODE
    assert tuple(app.value for app in result.request.requested_scope.apps) == (
        "shop",
        "crm",
    )
    assert type(result.request.redirect_target).__name__ == "OAuthRedirectMissing"


def test_token_request_requires_nonfalsy_redirect_uri() -> None:
    Service, _, Rejected, _ = _modules()
    for raw in ("", "0"):
        result = Service().parse(
            query(
                client_id="client",
                client_name="Client",
                response_type="token",
                scope="shop",
                redirect_uri=raw,
            )
        )
        assert isinstance(result, Rejected)


def test_unsupported_response_type_is_rejected() -> None:
    Service, _, Rejected, _ = _modules()
    result = Service().parse(
        query(
            client_id="client",
            client_name="Client",
            response_type="wat",
            scope="shop",
        )
    )
    assert isinstance(result, Rejected)


def test_code_redirect_appends_query_without_reencoding_existing_uri() -> None:
    _, _, _, Redirects = _modules()
    from gomazon_webasyst.application.oauth_authorization.vo.authorization import (
        OAuthRedirectUri,
    )

    result = Redirects().code(
        OAuthRedirectUri("https://client.test/cb?x=1#frag"),
        AuthorizationCode("abc"),
    )
    assert result.location == "https://client.test/cb?x=1#frag&code=abc"


def test_code_error_query_and_token_fragment_are_plain_legacy_concatenation() -> None:
    _, _, _, Redirects = _modules()
    from gomazon_webasyst.application.oauth_authorization.vo.authorization import (
        OAuthRedirectUri,
    )

    redirects = Redirects()
    uri = OAuthRedirectUri("https://client.test/cb?x=1")
    assert redirects.error_query(uri).location == (
        "https://client.test/cb?x=1&error=access_denied"
    )
    assert redirects.error_fragment(uri).location == (
        "https://client.test/cb?x=1#error=access_denied"
    )
