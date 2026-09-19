import pytest

from gomazon_webasyst.application.api_credential_values import ApiAccessToken
from gomazon_webasyst.application.api_execution.vo.parameters import ApiParameterMap, ApiRequestParameters
from gomazon_webasyst.compatibility.webasyst.api.services.credential_extractor import (
    ApiCredentialExtracted,
    ApiCredentialMissing,
    LegacyApiCredentialExtractionService,
)
from gomazon_webasyst.compatibility.webasyst.api.services.parameter_reader import (
    ApiParameterRead,
    ApiParameterRejected,
    ApiParameterReaderService,
)
from gomazon_webasyst.compatibility.webasyst.api.services.response_format import (
    ApiResponseFormatRejected,
    ApiResponseFormatResolved,
    LegacyApiResponseFormatService,
)
from gomazon_webasyst.compatibility.webasyst.api.services.target_parser import (
    ApiTargetMalformed,
    ApiTargetParsed,
    ApiTargetReservedEndpoint,
    LegacyApiTargetParser,
)
from gomazon_webasyst.compatibility.webasyst.api.vo.transport import (
    AuthorizationHeader,
    NoAuthorizationHeader,
    NoRequestedResponseFormat,
    RequestedResponseFormat,
)
from gomazon_webasyst.contracts.enums import ApiCredentialSourceKind, ApiFrameworkErrorCode, ApiResponseFormat


def test_post_access_token_shadows_get_even_when_empty_then_header_wins() -> None:
    result = LegacyApiCredentialExtractionService().extract(
        query=ApiParameterMap({"access_token": "get-token"}),
        form=ApiParameterMap({"access_token": ""}),
        authorization=AuthorizationHeader("Bearer header-token"),
        server_authorization=NoAuthorizationHeader(),
    )
    assert isinstance(result, ApiCredentialExtracted)
    assert result.token == ApiAccessToken("header-token")
    assert result.source is ApiCredentialSourceKind.AUTHORIZATION_HEADER


def test_nonempty_post_beats_get_and_header() -> None:
    result = LegacyApiCredentialExtractionService().extract(
        query=ApiParameterMap({"access_token": "get-token"}),
        form=ApiParameterMap({"access_token": "post-token"}),
        authorization=AuthorizationHeader("Bearer header-token"),
        server_authorization=NoAuthorizationHeader(),
    )
    assert isinstance(result, ApiCredentialExtracted)
    assert result.token == ApiAccessToken("post-token")
    assert result.source is ApiCredentialSourceKind.REQUEST


def test_no_post_key_uses_get_before_header() -> None:
    result = LegacyApiCredentialExtractionService().extract(
        query=ApiParameterMap({"access_token": "get-token"}),
        form=ApiParameterMap({}),
        authorization=AuthorizationHeader("Bearer header-token"),
        server_authorization=NoAuthorizationHeader(),
    )
    assert isinstance(result, ApiCredentialExtracted)
    assert result.token == ApiAccessToken("get-token")


def test_request_zero_is_php_falsy_and_bearer_is_case_insensitive() -> None:
    result = LegacyApiCredentialExtractionService().extract(
        query=ApiParameterMap({"access_token": "0"}),
        form=ApiParameterMap({}),
        authorization=AuthorizationHeader("  bEaReR   header-token  "),
        server_authorization=NoAuthorizationHeader(),
    )
    assert isinstance(result, ApiCredentialExtracted)
    assert result.token == ApiAccessToken("header-token")


def test_missing_all_credential_sources_is_explicit() -> None:
    result = LegacyApiCredentialExtractionService().extract(
        query=ApiParameterMap({}),
        form=ApiParameterMap({}),
        authorization=NoAuthorizationHeader(),
        server_authorization=NoAuthorizationHeader(),
    )
    assert isinstance(result, ApiCredentialMissing)


@pytest.mark.parametrize(
    ("path", "query", "app", "method"),
    [
        ("api.php", {"app": "shop", "method": "order.get"}, "shop", "order.get"),
        ("api.php/shop/order.get", {}, "shop", "order.get"),
        ("api.php/shop.order.get", {}, "shop", "order.get"),
    ],
)
def test_target_parser_normalizes_three_legacy_forms(path, query, app, method) -> None:
    result = LegacyApiTargetParser().parse(path, ApiParameterMap(query))
    assert isinstance(result, ApiTargetParsed)
    assert result.target.app_id.value == app
    assert result.target.method.value == method


@pytest.mark.parametrize("path", ["api.php/auth", "api.php/token", "api.php/revoke", "api.php/token-headless", "api.php/cron/app/job"])
def test_target_parser_keeps_reserved_endpoints_out_of_method_execution(path) -> None:
    assert isinstance(
        LegacyApiTargetParser().parse(path, ApiParameterMap({})),
        ApiTargetReservedEndpoint,
    )


def test_malformed_target_is_explicit() -> None:
    assert isinstance(
        LegacyApiTargetParser().parse("api.php/too/many/parts", ApiParameterMap({})),
        ApiTargetMalformed,
    )


def test_response_format_defaults_and_normalizes() -> None:
    service = LegacyApiResponseFormatService()
    default = service.resolve(NoRequestedResponseFormat())
    xml = service.resolve(RequestedResponseFormat("XmL"))
    invalid = service.resolve(RequestedResponseFormat("yaml"))
    assert isinstance(default, ApiResponseFormatResolved)
    assert default.format is ApiResponseFormat.JSON
    assert isinstance(xml, ApiResponseFormatResolved)
    assert xml.format is ApiResponseFormat.XML
    assert isinstance(invalid, ApiResponseFormatRejected)
    assert invalid.error.code is ApiFrameworkErrorCode.INVALID_REQUEST


@pytest.mark.parametrize("value", ["", "0", 0, 0.0, False, (), {}])
def test_required_parameter_uses_php_falsy_semantics(value) -> None:
    params = ApiRequestParameters(
        query=ApiParameterMap({"value": value}),
        form=ApiParameterMap({}),
    )
    result = ApiParameterReaderService().get(params, "value", required=True)
    assert isinstance(result, ApiParameterRejected)
    assert result.error.code is ApiFrameworkErrorCode.INVALID_PARAM


def test_get_and_post_never_cross_parameter_sources() -> None:
    params = ApiRequestParameters(
        query=ApiParameterMap({"value": "query"}),
        form=ApiParameterMap({"value": "form"}),
    )
    reader = ApiParameterReaderService()
    get_result = reader.get(params, "value", required=True)
    post_result = reader.post(params, "value", required=True)
    assert isinstance(get_result, ApiParameterRead)
    assert get_result.value == "query"
    assert isinstance(post_result, ApiParameterRead)
    assert post_result.value == "form"
