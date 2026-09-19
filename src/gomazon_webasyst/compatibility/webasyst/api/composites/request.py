from dataclasses import dataclass

from gomazon_webasyst.application.api_execution.vo.method import ApiHttpMethod
from gomazon_webasyst.application.api_execution.vo.parameters import ApiParameterMap
from gomazon_webasyst.compatibility.webasyst.api.vo.transport import (
    ApiJsonpCallback,
    AuthorizationHeaderState,
    RequestedResponseFormatState,
)


@dataclass(slots=True, frozen=True)
class LegacyApiHttpRequestComposite:
    request_path: str
    query: ApiParameterMap
    form: ApiParameterMap
    authorization_header: AuthorizationHeaderState
    server_authorization: AuthorizationHeaderState
    http_method: ApiHttpMethod
    is_https: bool
    requested_format: RequestedResponseFormatState
    callback: ApiJsonpCallback
