from dataclasses import dataclass
from typing import Annotated, Literal, TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_serializer,
    field_validator,
)

from gomazon_webasyst.contracts.enums import (
    ApiExecutionResultKind,
    ApiFrameworkErrorCode,
    ApiMethodResultKind,
)


@dataclass(slots=True, frozen=True)
class ApiApplicationErrorCode:
    value: str

    def __post_init__(self) -> None:
        if not self.value or self.value != self.value.strip():
            raise ValueError(
                "api application error code must be non-empty and trimmed"
            )


class ApiFrameworkError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: ApiFrameworkErrorCode
    description: str
    http_status: Annotated[int, Field(ge=100, le=599)]
    details: dict[str, JsonValue]


class ApiMethodError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: ApiApplicationErrorCode
    description: str
    http_status: Annotated[int, Field(ge=100, le=599)]
    details: dict[str, JsonValue]

    @field_validator("code", mode="before")
    @classmethod
    def parse_code(cls, value):
        if isinstance(value, str):
            return ApiApplicationErrorCode(value)
        return value

    @field_serializer("code")
    def serialize_code(
        self,
        value: ApiApplicationErrorCode,
    ) -> str:
        return value.value


ApiError: TypeAlias = Annotated[
    ApiFrameworkError | ApiMethodError,
    Field(union_mode="left_to_right"),
]


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
