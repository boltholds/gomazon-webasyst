import json
from importlib import import_module

import pytest

from gomazon_webasyst.application.api_credential_values import (
    ApiAccessToken,
    ApiScope,
)
from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiParameterMap,
    ApiRequestParameters,
)
from gomazon_webasyst.contracts.api_credentials import (
    AuthorizationCodeExchangeRejected,
    AuthorizationCodeExchanged,
)
from gomazon_webasyst.contracts.enums import (
    ApiResponseFormat,
    AuthorizationCodeExchangeRejectReason,
)


def _module():
    try:
        return import_module(
            "gomazon_webasyst.compatibility.webasyst.oauth.services.token_controller"
        )
    except ModuleNotFoundError as error:
        pytest.fail(f"legacy oauth token controller missing: {error}")


class Exchange:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def __call__(self, code, client_id):
        self.calls.append((code, client_id))
        return self.result


def params():
    return ApiRequestParameters(
        query=ApiParameterMap({"callback": "cb"}),
        form=ApiParameterMap(
            {
                "code": "c" * 32,
                "client_id": "client",
                "grant_type": "authorization_code",
            }
        ),
    )


@pytest.mark.asyncio
async def test_success_payload_contains_only_access_token() -> None:
    m = _module()
    exchange = Exchange(
        AuthorizationCodeExchanged(
            access_token=ApiAccessToken("a" * 32),
            scope=ApiScope((AppId("shop"),)),
        )
    )
    response = await m.LegacyOAuthTokenController(exchange).execute(
        params(),
        ApiResponseFormat.JSON,
    )
    assert response.status_code == 200
    assert response.payload == {"access_token": "a" * 32}
    assert len(exchange.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reason",
    [
        AuthorizationCodeExchangeRejectReason.NOT_FOUND,
        AuthorizationCodeExchangeRejectReason.CLIENT_MISMATCH,
        AuthorizationCodeExchangeRejectReason.EXPIRED,
        AuthorizationCodeExchangeRejectReason.TOKEN_COLLISION,
        AuthorizationCodeExchangeRejectReason.CONCURRENT_STATE_CHANGED,
        AuthorizationCodeExchangeRejectReason.CODE_STATE_CHANGED,
    ],
)
async def test_exchange_rejections_map_to_invalid_grant(reason) -> None:
    m = _module()
    response = await m.LegacyOAuthTokenController(
        Exchange(AuthorizationCodeExchangeRejected(reason=reason))
    ).execute(params(), ApiResponseFormat.JSON)
    assert response.status_code == 200
    assert response.payload["error"] == "invalid_grant"


def test_callback_does_not_enable_jsonp_for_controller_renderer() -> None:
    m = _module()
    renderer = m.LegacyOAuthControllerRenderer()
    response = renderer.render(
        payload={"error": "invalid_grant"},
        response_format=ApiResponseFormat.JSON,
    )
    assert response.status_code == 200
    assert response.media_type == "application/json; charset=utf-8"
    assert response.body.startswith("{")
    assert not response.body.startswith("cb(")


def test_xml_controller_renderer_uses_legacy_xml_formatter() -> None:
    m = _module()
    response = m.LegacyOAuthControllerRenderer().render(
        payload={"access_token": "abc"},
        response_format=ApiResponseFormat.XML,
    )
    assert response.status_code == 200
    assert response.media_type == "application/xml; charset=utf-8"
    assert "<access_token>abc</access_token>" in response.body
