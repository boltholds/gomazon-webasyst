from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, JsonValue, RootModel, field_validator

from gomazon_webasyst.contracts.enums import (
    ApiExecutionResultKind,
    ApiFrameworkErrorCode,
    ApiMethodResultKind,
)


class ApiMethodErrorCode(RootModel[str]):
    model_config = ConfigDict(frozen=True)

    @field_validator("root")
    @classmethod
    def validate_value(cls, value: str) -> str:
        if not value:
            raise ValueError("API method error code must not be empty")
        return value

    @property
    def value(self) -> str:
        return self.root


class ApiFrameworkError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: ApiFrameworkErrorCode
    description: str
    http_status: Annotated[int, Field(ge=100, le=599)]
    details: dict[str, JsonValue]


class ApiMethodError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: ApiMethodErrorCode
    description: str
    http_status: Annotated[int, Field(ge=100, le=599)]
    details: dict[str, JsonValue]


ApiError: TypeAlias = ApiFrameworkError | ApiMethodError


class ApiExecutionSucceeded(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[ApiExecutionResultKind.SUCCEEDED] = ApiExecutionResultKind.SUCCEEDED
    payload: JsonValue
    status_code: Annotated[int, Field(ge=100, le=599)] = 200


class ApiExecutionRejected(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[ApiExecutionResultKind.REJECTED] = ApiExecutionResultKind.REJECTED
    error: ApiError


ApiExecutionResult: TypeAlias = Annotated[
    ApiExecutionSucceeded | ApiExecutionRejected,
    Field(discriminator="kind"),
]


class ApiMethodSucceeded(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[ApiMethodResultKind.SUCCEEDED] = ApiMethodResultKind.SUCCEEDED
    payload: JsonValue
    status_code: Annotated[int, Field(ge=100, le=599)] = 200


class ApiMethodRejected(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[ApiMethodResultKind.REJECTED] = ApiMethodResultKind.REJECTED
    error: ApiError


ApiMethodResult: TypeAlias = Annotated[
    ApiMethodSucceeded | ApiMethodRejected,
    Field(discriminator="kind"),
]
