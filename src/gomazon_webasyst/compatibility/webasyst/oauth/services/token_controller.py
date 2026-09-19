from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.application.api_credential_values import (
    ApiClientId,
    AuthorizationCode,
)
from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiParameterMap,
    ApiParameterValue,
    ApiRequestParameters,
)
from gomazon_webasyst.compatibility.webasyst.api.services.json_formatter import (
    LegacyJsonApiFormatter,
)
from gomazon_webasyst.compatibility.webasyst.api.services.xml_formatter import (
    LegacyXmlApiFormatter,
)
from gomazon_webasyst.compatibility.webasyst.oauth.composites.controller_response import (
    OAuthControllerPayloadResponse,
    OAuthControllerRenderedResponse,
)
from gomazon_webasyst.contracts.api_credentials import (
    AuthorizationCodeExchangeRejected,
    AuthorizationCodeExchanged,
)
from gomazon_webasyst.contracts.enums import (
    ApiResponseFormat,
    OAuthControllerErrorCode,
    OAuthGrantType,
)


@dataclass(slots=True, frozen=True)
class OAuthTokenExchangeRequestParsed:
    code: AuthorizationCode
    client_id: ApiClientId


@dataclass(slots=True, frozen=True)
class OAuthTokenExchangeRequestRejected:
    payload: dict[str, str]


OAuthTokenExchangeRequestParseResult: TypeAlias = (
    OAuthTokenExchangeRequestParsed | OAuthTokenExchangeRequestRejected
)


def _php_falsy(value: ApiParameterValue) -> bool:
    if value is False or value == 0 or value == 0.0:
        return True
    if isinstance(value, str):
        return value in {"", "0"}
    if isinstance(value, tuple | Mapping):
        return len(value) == 0
    return False


class LegacyOAuthTokenRequestService:
    def parse(
        self,
        parameters: ApiRequestParameters,
    ) -> OAuthTokenExchangeRequestParseResult:
        form = parameters.form
        required = ("code", "client_id", "grant_type")
        values: dict[str, ApiParameterValue] = {}
        for name in required:
            if name not in form or _php_falsy(form[name]):
                return OAuthTokenExchangeRequestRejected(
                    payload={
                        "error": OAuthControllerErrorCode.INVALID_REQUEST.value,
                        "error_description": f"Required parameter is missing: {name}",
                    }
                )
            values[name] = form[name]

        if not all(isinstance(values[name], str) for name in required):
            return OAuthTokenExchangeRequestRejected(
                payload={
                    "error": OAuthControllerErrorCode.INVALID_REQUEST.value,
                    "error_description": "Invalid token request",
                }
            )

        grant_type = str(values["grant_type"])
        if grant_type != OAuthGrantType.AUTHORIZATION_CODE.value:
            return OAuthTokenExchangeRequestRejected(
                payload={
                    "error": OAuthControllerErrorCode.UNSUPPORTED_GRANT_TYPE.value,
                    "error_description": f"Unsupported grant type: {grant_type}",
                }
            )

        try:
            code = AuthorizationCode(str(values["code"]))
            client_id = ApiClientId(str(values["client_id"]))
        except ValueError:
            return OAuthTokenExchangeRequestRejected(
                payload={
                    "error": OAuthControllerErrorCode.INVALID_REQUEST.value,
                    "error_description": "Invalid token request",
                }
            )
        return OAuthTokenExchangeRequestParsed(code=code, client_id=client_id)


class LegacyOAuthTokenController:
    def __init__(self, exchange_authorization_code) -> None:
        self._exchange_authorization_code = exchange_authorization_code
        self._request_service = LegacyOAuthTokenRequestService()

    async def execute(
        self,
        parameters: ApiRequestParameters,
        response_format: ApiResponseFormat,
    ) -> OAuthControllerPayloadResponse:
        parsed = self._request_service.parse(parameters)
        if isinstance(parsed, OAuthTokenExchangeRequestRejected):
            return OAuthControllerPayloadResponse(
                status_code=200,
                payload=parsed.payload,
                format=response_format,
            )

        result = await self._exchange_authorization_code(
            parsed.code,
            parsed.client_id,
        )
        if isinstance(result, AuthorizationCodeExchanged):
            return OAuthControllerPayloadResponse(
                status_code=200,
                payload={"access_token": result.access_token.value},
                format=response_format,
            )
        if isinstance(result, AuthorizationCodeExchangeRejected):
            return OAuthControllerPayloadResponse(
                status_code=200,
                payload={
                    "error": OAuthControllerErrorCode.INVALID_GRANT.value,
                    "error_description": "Invalid grant",
                },
                format=response_format,
            )
        raise AssertionError("unsupported authorization code exchange result")


class LegacyOAuthControllerRenderer:
    def __init__(self) -> None:
        self._json = LegacyJsonApiFormatter()
        self._xml = LegacyXmlApiFormatter()

    def render(
        self,
        *,
        payload: dict[str, str],
        response_format: ApiResponseFormat,
    ) -> OAuthControllerRenderedResponse:
        if response_format is ApiResponseFormat.JSON:
            return OAuthControllerRenderedResponse(
                status_code=200,
                media_type="application/json; charset=utf-8",
                body=self._json.format(payload),
            )
        if response_format is ApiResponseFormat.XML:
            return OAuthControllerRenderedResponse(
                status_code=200,
                media_type="application/xml; charset=utf-8",
                body=self._xml.format(payload),
            )
        raise AssertionError("unsupported oauth controller response format")
