from gomazon_webasyst.application.api_execution.composites.results import (
    ApiExecutionRejected,
    ApiExecutionResult,
    ApiExecutionSucceeded,
)
from gomazon_webasyst.compatibility.webasyst.api.composites.response import ApiTransportResponse
from gomazon_webasyst.compatibility.webasyst.api.services.error_mapper import LegacyApiErrorMapper
from gomazon_webasyst.compatibility.webasyst.api.services.json_formatter import LegacyJsonApiFormatter
from gomazon_webasyst.compatibility.webasyst.api.services.xml_formatter import LegacyXmlApiFormatter
from gomazon_webasyst.compatibility.webasyst.api.vo.transport import ApiJsonpCallback
from gomazon_webasyst.contracts.enums import ApiResponseFormat


def _php_truthy_string(value: str) -> bool:
    return value != "" and value != "0"


class LegacyApiResponseRenderer:
    def __init__(self) -> None:
        self._errors = LegacyApiErrorMapper()
        self._json = LegacyJsonApiFormatter()
        self._xml = LegacyXmlApiFormatter()

    def render(
        self,
        result: ApiExecutionResult,
        response_format: ApiResponseFormat,
        callback: ApiJsonpCallback,
    ) -> ApiTransportResponse:
        if isinstance(result, ApiExecutionRejected):
            payload = self._errors.payload(result.error)
            status_code = result.error.http_status
        else:
            assert isinstance(result, ApiExecutionSucceeded)
            payload = result.payload
            status_code = result.status_code

        if response_format is ApiResponseFormat.XML:
            return ApiTransportResponse(
                status_code=status_code,
                media_type="text/xml; charset=utf-8",
                body=self._xml.format(payload),
            )

        body = self._json.format(payload)
        if _php_truthy_string(callback.value):
            return ApiTransportResponse(
                status_code=200,
                media_type="text/javascript; charset=utf-8",
                body=f"{callback.value}({body});",
            )
        return ApiTransportResponse(
            status_code=status_code,
            media_type="application/json; charset=utf-8",
            body=body,
        )
