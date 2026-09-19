from dataclasses import dataclass
from typing import TypeAlias


@dataclass(slots=True, frozen=True)
class ApiTransportAccepted:
    pass


@dataclass(slots=True, frozen=True)
class ApiTransportDisabled:
    message: str


@dataclass(slots=True, frozen=True)
class ApiHttpsRequired:
    pass


ApiTransportPreconditionResult: TypeAlias = (
    ApiTransportAccepted | ApiTransportDisabled | ApiHttpsRequired
)


class LegacyApiTransportPreconditionService:
    def __init__(
        self,
        *,
        api_enabled: bool,
        disable_message: str,
        force_https: bool,
    ) -> None:
        self._api_enabled = api_enabled
        self._disable_message = disable_message
        self._force_https = force_https

    def evaluate(self, *, is_https: bool) -> ApiTransportPreconditionResult:
        if not self._api_enabled:
            return ApiTransportDisabled(
                message=self._disable_message or "API is disabled"
            )
        if self._force_https and not is_https:
            return ApiHttpsRequired()
        return ApiTransportAccepted()
