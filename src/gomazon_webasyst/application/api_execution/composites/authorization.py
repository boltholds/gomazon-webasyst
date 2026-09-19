from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.contracts.api_execution import ApiFrameworkError


@dataclass(slots=True, frozen=True)
class ApiAuthorizationGranted:
    pass


@dataclass(slots=True, frozen=True)
class ApiAuthorizationRejected:
    error: ApiFrameworkError


ApiAuthorizationResult: TypeAlias = ApiAuthorizationGranted | ApiAuthorizationRejected
