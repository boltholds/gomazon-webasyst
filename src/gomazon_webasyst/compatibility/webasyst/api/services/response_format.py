from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.compatibility.webasyst.api.vo.transport import (
    NoRequestedResponseFormat,
    RequestedResponseFormat,
    RequestedResponseFormatState,
)
from gomazon_webasyst.contracts.api_execution import ApiFrameworkError
from gomazon_webasyst.contracts.enums import ApiFrameworkErrorCode, ApiResponseFormat


@dataclass(slots=True, frozen=True)
class ApiResponseFormatResolved:
    format: ApiResponseFormat


@dataclass(slots=True, frozen=True)
class ApiResponseFormatRejected:
    error: ApiFrameworkError


ApiResponseFormatResolution: TypeAlias = ApiResponseFormatResolved | ApiResponseFormatRejected


class LegacyApiResponseFormatService:
    def resolve(self, requested: RequestedResponseFormatState) -> ApiResponseFormatResolution:
        if isinstance(requested, NoRequestedResponseFormat):
            return ApiResponseFormatResolved(format=ApiResponseFormat.JSON)
        assert isinstance(requested, RequestedResponseFormat)
        normalized = requested.value.lower()
        if normalized == ApiResponseFormat.JSON.value:
            return ApiResponseFormatResolved(format=ApiResponseFormat.JSON)
        if normalized == ApiResponseFormat.XML.value:
            return ApiResponseFormatResolved(format=ApiResponseFormat.XML)
        return ApiResponseFormatRejected(
            error=ApiFrameworkError(
                code=ApiFrameworkErrorCode.INVALID_REQUEST,
                description=f"Invalid response format: {requested.value.upper()}",
                http_status=400,
                details={},
            )
        )
