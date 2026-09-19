from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_execution.vo.method import ApiMethodName, ApiMethodTarget
from gomazon_webasyst.application.api_execution.vo.parameters import ApiParameterMap


_RESERVED = {
    "auth",
    "token",
    "revoke",
    "token-headless",
    "license-cache",
    "profile-update",
}


@dataclass(slots=True, frozen=True)
class ApiTargetParsed:
    target: ApiMethodTarget


@dataclass(slots=True, frozen=True)
class ApiTargetMalformed:
    request_path: str


@dataclass(slots=True, frozen=True)
class ApiTargetReservedEndpoint:
    endpoint: str


ApiTargetParseResult: TypeAlias = (
    ApiTargetParsed | ApiTargetMalformed | ApiTargetReservedEndpoint
)


class LegacyApiTargetParser:
    def parse(
        self,
        request_path: str,
        query: ApiParameterMap,
    ) -> ApiTargetParseResult:
        path = request_path.strip("/")
        if path.startswith("api.php/cron/"):
            return ApiTargetReservedEndpoint(endpoint=path.removeprefix("api.php/"))
        if path.startswith("api.php/"):
            tail = path.removeprefix("api.php/")
            if tail in _RESERVED:
                return ApiTargetReservedEndpoint(endpoint=tail)

        if path == "api.php":
            if "app" not in query or "method" not in query:
                return ApiTargetMalformed(request_path=path)
            app = query["app"]
            method = query["method"]
            if not isinstance(app, str) or not isinstance(method, str):
                return ApiTargetMalformed(request_path=path)
            return self._target(path, app, method)

        parts = path.split("/")
        if len(parts) == 3 and parts[0] == "api.php":
            return self._target(path, parts[1], parts[2])
        if len(parts) == 2 and parts[0] == "api.php" and "." in parts[1]:
            app, method = parts[1].split(".", 1)
            return self._target(path, app, method)
        return ApiTargetMalformed(request_path=path)

    @staticmethod
    def _target(path: str, app: str, method: str) -> ApiTargetParseResult:
        try:
            return ApiTargetParsed(
                target=ApiMethodTarget(
                    app_id=AppId(app),
                    method=ApiMethodName(method),
                )
            )
        except ValueError:
            return ApiTargetMalformed(request_path=path)
