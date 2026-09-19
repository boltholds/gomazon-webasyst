from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_credential_values import ApiClientId
from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiParameterMap,
    ApiParameterValue,
)
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
from gomazon_webasyst.contracts.api_execution import ApiFrameworkError
from gomazon_webasyst.contracts.enums import ApiFrameworkErrorCode, OAuthResponseType


@dataclass(slots=True, frozen=True)
class OAuthAuthorizationRequestParsed:
    request: OAuthAuthorizationRequest


@dataclass(slots=True, frozen=True)
class OAuthAuthorizationRequestRejected:
    error: ApiFrameworkError


OAuthAuthorizationRequestParseResult: TypeAlias = (
    OAuthAuthorizationRequestParsed | OAuthAuthorizationRequestRejected
)


def _php_falsy(value: ApiParameterValue) -> bool:
    if value is False or value == 0 or value == 0.0:
        return True
    if isinstance(value, str):
        return value in {"", "0"}
    if isinstance(value, tuple | Mapping):
        return len(value) == 0
    return False


class LegacyOAuthAuthorizationRequestService:
    def parse(
        self,
        query: ApiParameterMap,
    ) -> OAuthAuthorizationRequestParseResult:
        required = ("client_id", "client_name", "response_type", "scope")
        values: dict[str, ApiParameterValue] = {}
        for name in required:
            if name not in query or _php_falsy(query[name]):
                return self._rejected(f"Required parameter is missing: {name}")
            values[name] = query[name]

        if not all(isinstance(values[name], str) for name in required):
            return self._rejected("Invalid authorization request")

        raw_response_type = str(values["response_type"])
        try:
            response_type = OAuthResponseType(raw_response_type)
        except ValueError:
            return self._rejected(
                f"Unsupported response type: {raw_response_type}"
            )

        raw_redirect: ApiParameterValue = (
            query["redirect_uri"] if "redirect_uri" in query else ""
        )
        if response_type is OAuthResponseType.TOKEN and _php_falsy(raw_redirect):
            return self._rejected("Required parameter is missing: redirect_uri")
        if raw_redirect != "" and not isinstance(raw_redirect, str):
            return self._rejected("Invalid redirect_uri")

        raw_scope = str(values["scope"])
        apps = tuple(
            AppId(item)
            for item in raw_scope.split(",")
            if item
        )
        if not apps:
            return self._rejected("Invalid scope")

        redirect_target = (
            OAuthRedirectProvided(OAuthRedirectUri(raw_redirect))
            if isinstance(raw_redirect, str) and raw_redirect not in {"", "0"}
            else OAuthRedirectMissing()
        )
        return OAuthAuthorizationRequestParsed(
            request=OAuthAuthorizationRequest(
                client_id=ApiClientId(str(values["client_id"])),
                client_name=OAuthClientName(str(values["client_name"])),
                response_type=response_type,
                requested_scope=OAuthRequestedScope(apps),
                redirect_target=redirect_target,
            )
        )

    @staticmethod
    def _rejected(description: str) -> OAuthAuthorizationRequestRejected:
        return OAuthAuthorizationRequestRejected(
            error=ApiFrameworkError(
                code=ApiFrameworkErrorCode.INVALID_REQUEST,
                description=description,
                http_status=400,
                details={},
            )
        )
