from dataclasses import dataclass

from gomazon_webasyst.application.api_credential_values import ApiAccessToken, ApiClientId, ApiScope
from gomazon_webasyst.application.api_execution.vo.method import ApiHttpMethod, ApiMethodTarget
from gomazon_webasyst.application.api_execution.vo.parameters import ApiRequestParameters
from gomazon_webasyst.application.api_execution.vo.origin import ApiRequestOrigin


@dataclass(slots=True, frozen=True)
class ApiInvocationRequest:
    access_token: ApiAccessToken
    target: ApiMethodTarget
    http_method: ApiHttpMethod
    parameters: ApiRequestParameters
    origin: ApiRequestOrigin


@dataclass(slots=True, frozen=True)
class ApiPrincipalContext:
    contact_id: int
    client_id: ApiClientId
    scope: ApiScope

    def __post_init__(self) -> None:
        if self.contact_id <= 0:
            raise ValueError("api principal contact id must be positive")


@dataclass(slots=True, frozen=True)
class ApiInvocationContext:
    principal: ApiPrincipalContext
    target: ApiMethodTarget
    origin: ApiRequestOrigin
