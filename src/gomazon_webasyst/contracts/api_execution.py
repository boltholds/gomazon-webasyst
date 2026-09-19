from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from gomazon_webasyst.contracts.enums import (
    ApiExecutionResultKind,
    ApiFrameworkErrorCode,
    ApiMethodResultKind,
)


class ApiFrameworkError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: ApiFrameworkErrorCode
    description: str
    http_status: Annotated[int, Field(ge=100, le=599)]
    details: dict[str, JsonValue]


class ApiExecutionSucceeded(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[ApiExecutionResultKind.SUCCEEDED] = ApiExecutionResultKind.SUCCEEDED
    payload: JsonValue
    status_code: Annotated[int, Field(ge=100, le=599)] = 200


class ApiExecutionRejected(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[ApiExecutionResultKind.REJECTED] = ApiExecutionResultKind.REJECTED
    error: ApiFrameworkError


ApiExecutionResult: TypeAlias = Annotated[
    ApiExecutionSucceeded | ApiExecutionRejected,
    Field(discriminator="kind"),
]


class ApiMethodSucceeded(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[ApiMethodResultKind.SUCCEEDED] = ApiMethodResultKind.SUCCEEDED
    payload: Any
    status_code: Annotated[int, Field(ge=100, le=599)] = 200


class ApiMethodRejected(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[ApiMethodResultKind.REJECTED] = ApiMethodResultKind.REJECTED
    error: ApiFrameworkError


ApiMethodResult: TypeAlias = Annotated[
    ApiMethodSucceeded | ApiMethodRejected,
    Field(discriminator="kind"),
]
