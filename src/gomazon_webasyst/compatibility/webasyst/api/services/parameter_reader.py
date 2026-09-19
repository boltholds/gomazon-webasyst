from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiParameterMap,
    ApiParameterValue,
    ApiRequestParameters,
)
from gomazon_webasyst.contracts.api_execution import ApiFrameworkError
from gomazon_webasyst.contracts.enums import ApiFrameworkErrorCode


@dataclass(slots=True, frozen=True)
class ApiParameterRead:
    name: str
    value: ApiParameterValue


@dataclass(slots=True, frozen=True)
class ApiParameterMissing:
    name: str


@dataclass(slots=True, frozen=True)
class ApiParameterRejected:
    error: ApiFrameworkError


ApiParameterReadResult: TypeAlias = ApiParameterRead | ApiParameterMissing | ApiParameterRejected


def _php_falsy(value: ApiParameterValue) -> bool:
    if value is False or value == 0 or value == 0.0:
        return True
    if isinstance(value, str):
        return value == "" or value == "0"
    if isinstance(value, tuple):
        return len(value) == 0
    if isinstance(value, Mapping):
        return len(value) == 0
    return False


class ApiParameterReaderService:
    def get(
        self,
        parameters: ApiRequestParameters,
        name: str,
        *,
        required: bool = False,
    ) -> ApiParameterReadResult:
        return self._read(parameters.query, name, required)

    def post(
        self,
        parameters: ApiRequestParameters,
        name: str,
        *,
        required: bool = False,
    ) -> ApiParameterReadResult:
        return self._read(parameters.form, name, required)

    @staticmethod
    def _read(
        source: ApiParameterMap,
        name: str,
        required: bool,
    ) -> ApiParameterReadResult:
        if name not in source:
            if required:
                return ApiParameterReaderService._rejected(name)
            return ApiParameterMissing(name=name)
        value = source[name]
        if required and _php_falsy(value):
            return ApiParameterReaderService._rejected(name)
        return ApiParameterRead(name=name, value=value)

    @staticmethod
    def _rejected(name: str) -> ApiParameterRejected:
        return ApiParameterRejected(
            error=ApiFrameworkError(
                code=ApiFrameworkErrorCode.INVALID_PARAM,
                description=f"Required parameter is missing: {name}",
                http_status=400,
                details={"parameter": name},
            )
        )
