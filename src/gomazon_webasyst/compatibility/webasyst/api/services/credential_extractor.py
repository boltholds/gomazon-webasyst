from dataclasses import dataclass
import re
from typing import TypeAlias

from gomazon_webasyst.application.api_credential_values import ApiAccessToken
from gomazon_webasyst.application.api_execution.vo.parameters import ApiParameterMap
from gomazon_webasyst.compatibility.webasyst.api.vo.transport import (
    AuthorizationHeader,
    AuthorizationHeaderState,
)
from gomazon_webasyst.contracts.enums import ApiCredentialSourceKind


_BEARER = re.compile(r"^\s*Bearer\s+", re.IGNORECASE)


@dataclass(slots=True, frozen=True)
class ApiCredentialExtracted:
    token: ApiAccessToken
    source: ApiCredentialSourceKind


@dataclass(slots=True, frozen=True)
class ApiCredentialMissing:
    pass


ApiCredentialExtractionResult: TypeAlias = ApiCredentialExtracted | ApiCredentialMissing


def _php_falsy(value: object) -> bool:
    if value is False or value == 0 or value == 0.0:
        return True
    if isinstance(value, str):
        return value == "" or value == "0"
    if isinstance(value, tuple):
        return len(value) == 0
    from collections.abc import Mapping
    if isinstance(value, Mapping):
        return len(value) == 0
    return False


def _request_string(value: object) -> str:
    if value is False:
        return ""
    if value is True:
        return "1"
    return str(value)


class LegacyApiCredentialExtractionService:
    def extract(
        self,
        *,
        query: ApiParameterMap,
        form: ApiParameterMap,
        authorization: AuthorizationHeaderState,
        server_authorization: AuthorizationHeaderState,
    ) -> ApiCredentialExtractionResult:
        selected: object = ""
        request_present = False
        if "access_token" in form:
            selected = form["access_token"]
            request_present = True
        elif "access_token" in query:
            selected = query["access_token"]
            request_present = True

        if request_present and not _php_falsy(selected):
            return ApiCredentialExtracted(
                token=ApiAccessToken(_request_string(selected)),
                source=ApiCredentialSourceKind.REQUEST,
            )

        for header, source in (
            (authorization, ApiCredentialSourceKind.AUTHORIZATION_HEADER),
            (server_authorization, ApiCredentialSourceKind.SERVER_AUTHORIZATION),
        ):
            if not isinstance(header, AuthorizationHeader):
                continue
            if _php_falsy(header.value):
                continue
            value = _BEARER.sub("", header.value).strip()
            if _php_falsy(value):
                continue
            return ApiCredentialExtracted(
                token=ApiAccessToken(value),
                source=source,
            )
        return ApiCredentialMissing()
