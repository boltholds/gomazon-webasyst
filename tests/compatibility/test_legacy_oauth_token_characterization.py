import pytest

from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiParameterMap,
    ApiRequestParameters,
)
from gomazon_webasyst.contracts.enums import ApiResponseFormat


def _modules():
    try:
        from gomazon_webasyst.compatibility.webasyst.oauth.services.controller_format import (
            LegacyOAuthControllerFormatService,
            OAuthControllerFormatRejected,
            OAuthControllerFormatResolved,
        )
        from gomazon_webasyst.compatibility.webasyst.oauth.services.token_controller import (
            LegacyOAuthTokenRequestService,
            OAuthTokenExchangeRequestParsed,
            OAuthTokenExchangeRequestRejected,
        )
        return (
            LegacyOAuthControllerFormatService,
            OAuthControllerFormatResolved,
            OAuthControllerFormatRejected,
            LegacyOAuthTokenRequestService,
            OAuthTokenExchangeRequestParsed,
            OAuthTokenExchangeRequestRejected,
        )
    except ModuleNotFoundError as error:
        pytest.fail(f"oauth token controller services missing: {error}")


def params(*, query=None, form=None):
    return ApiRequestParameters(
        query=ApiParameterMap(query or {}),
        form=ApiParameterMap(form or {}),
    )


def test_token_protocol_fields_are_post_only() -> None:
    _, _, _, RequestService, _, Rejected = _modules()
    result = RequestService().parse(
        params(
            query={
                "code": "c" * 32,
                "client_id": "client",
                "grant_type": "authorization_code",
            },
            form={},
        )
    )
    assert isinstance(result, Rejected)
    assert result.payload["error"] == "invalid_request"


def test_token_valid_form_fields_parse() -> None:
    _, _, _, RequestService, Parsed, _ = _modules()
    result = RequestService().parse(
        params(
            form={
                "code": "c" * 32,
                "client_id": "client",
                "grant_type": "authorization_code",
            }
        )
    )
    assert isinstance(result, Parsed)
    assert result.code.value == "c" * 32
    assert result.client_id.value == "client"


@pytest.mark.parametrize("field", ["code", "client_id", "grant_type"])
@pytest.mark.parametrize("value", ["", "0"])
def test_required_post_fields_use_php_falsy_semantics(field, value) -> None:
    _, _, _, RequestService, _, Rejected = _modules()
    form = {
        "code": "c" * 32,
        "client_id": "client",
        "grant_type": "authorization_code",
    }
    form[field] = value
    result = RequestService().parse(params(form=form))
    assert isinstance(result, Rejected)
    assert result.payload["error"] == "invalid_request"


def test_wrong_grant_type_is_unsupported_grant_type() -> None:
    _, _, _, RequestService, _, Rejected = _modules()
    result = RequestService().parse(
        params(
            form={
                "code": "c" * 32,
                "client_id": "client",
                "grant_type": "password",
            }
        )
    )
    assert isinstance(result, Rejected)
    assert result.payload["error"] == "unsupported_grant_type"


def test_controller_format_defaults_json_and_accepts_xml() -> None:
    Format, Resolved, _, _, _, _ = _modules()
    service = Format()
    default = service.resolve(ApiParameterMap({}))
    xml = service.resolve(ApiParameterMap({"format": "xml"}))
    assert isinstance(default, Resolved)
    assert default.format is ApiResponseFormat.JSON
    assert isinstance(xml, Resolved)
    assert xml.format is ApiResponseFormat.XML


def test_invalid_controller_format_is_json_invalid_request() -> None:
    Format, _, Rejected, _, _, _ = _modules()
    result = Format().resolve(ApiParameterMap({"format": "yaml"}))
    assert isinstance(result, Rejected)
    assert result.format is ApiResponseFormat.JSON
    assert result.payload == {
        "error": "invalid_request",
        "error_description": "Invalid format: YAML",
    }
