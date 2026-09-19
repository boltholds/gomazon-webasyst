from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.application.api_execution.vo.parameters import ApiParameterMap
from gomazon_webasyst.contracts.enums import (
    ApiResponseFormat,
    OAuthControllerErrorCode,
)


@dataclass(slots=True, frozen=True)
class OAuthControllerFormatResolved:
    format: ApiResponseFormat


@dataclass(slots=True, frozen=True)
class OAuthControllerFormatRejected:
    format: ApiResponseFormat
    payload: dict[str, str]


OAuthControllerFormatResult: TypeAlias = (
    OAuthControllerFormatResolved | OAuthControllerFormatRejected
)


class LegacyOAuthControllerFormatService:
    def resolve(self, query: ApiParameterMap) -> OAuthControllerFormatResult:
        if "format" not in query:
            return OAuthControllerFormatResolved(ApiResponseFormat.JSON)

        raw = query["format"]
        text = str(raw)
        normalized = text.lower()
        if normalized == ApiResponseFormat.JSON.value:
            return OAuthControllerFormatResolved(ApiResponseFormat.JSON)
        if normalized == ApiResponseFormat.XML.value:
            return OAuthControllerFormatResolved(ApiResponseFormat.XML)
        return OAuthControllerFormatRejected(
            format=ApiResponseFormat.JSON,
            payload={
                "error": OAuthControllerErrorCode.INVALID_REQUEST.value,
                "error_description": f"Invalid format: {text.upper()}",
            },
        )
