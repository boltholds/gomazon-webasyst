from datetime import datetime
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from gomazon_webasyst.application.api_credential_values import (
    ApiAccessToken,
    ApiClientId,
    ApiScope,
    AuthorizationCode,
)
from gomazon_webasyst.contracts.enums import (
    ApiTokenExpiryKind,
    ApiTokenLastUseKind,
    ApiTokenLookupKind,
    AuthorizationCodeExchangeKind,
    AuthorizationCodeExchangeRejectReason,
    AuthorizationCodeIssueKind,
    AuthorizationCodeIssueRejectReason,
)


class ApiTokenNeverExpires(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[ApiTokenExpiryKind.NEVER] = ApiTokenExpiryKind.NEVER


class ApiTokenExpiresAt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[ApiTokenExpiryKind.EXPIRES_AT] = ApiTokenExpiryKind.EXPIRES_AT
    at: datetime


ApiTokenExpiry: TypeAlias = Annotated[
    ApiTokenNeverExpires | ApiTokenExpiresAt,
    Field(discriminator="kind"),
]


class ApiTokenNeverUsed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[ApiTokenLastUseKind.NEVER_USED] = ApiTokenLastUseKind.NEVER_USED


class ApiTokenLastUsedAt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[ApiTokenLastUseKind.LAST_USED_AT] = ApiTokenLastUseKind.LAST_USED_AT
    at: datetime


ApiTokenLastUse: TypeAlias = Annotated[
    ApiTokenNeverUsed | ApiTokenLastUsedAt,
    Field(discriminator="kind"),
]


class StoredAuthorizationCode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    code: AuthorizationCode
    contact_id: Annotated[int, Field(gt=0)]
    client_id: ApiClientId
    scope: ApiScope
    expires_at: datetime


class StoredApiAccessToken(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    token: ApiAccessToken
    contact_id: Annotated[int, Field(gt=0)]
    client_id: ApiClientId
    scope: ApiScope
    created_at: datetime
    last_use: ApiTokenLastUse
    expiry: ApiTokenExpiry


class ApiTokenResolved(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[ApiTokenLookupKind.RESOLVED] = ApiTokenLookupKind.RESOLVED
    record: StoredApiAccessToken


class ApiTokenMissing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[ApiTokenLookupKind.MISSING] = ApiTokenLookupKind.MISSING
    token: ApiAccessToken


ApiTokenResolution: TypeAlias = Annotated[
    ApiTokenResolved | ApiTokenMissing,
    Field(discriminator="kind"),
]


class AuthorizationCodeIssued(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[AuthorizationCodeIssueKind.ISSUED] = AuthorizationCodeIssueKind.ISSUED
    record: StoredAuthorizationCode


class AuthorizationCodeIssueRejected(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[AuthorizationCodeIssueKind.REJECTED] = AuthorizationCodeIssueKind.REJECTED
    reason: AuthorizationCodeIssueRejectReason


AuthorizationCodeIssueResult: TypeAlias = Annotated[
    AuthorizationCodeIssued | AuthorizationCodeIssueRejected,
    Field(discriminator="kind"),
]


class AuthorizationCodeExchanged(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[AuthorizationCodeExchangeKind.EXCHANGED] = AuthorizationCodeExchangeKind.EXCHANGED
    access_token: ApiAccessToken
    scope: ApiScope


class AuthorizationCodeExchangeRejected(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[AuthorizationCodeExchangeKind.REJECTED] = AuthorizationCodeExchangeKind.REJECTED
    reason: AuthorizationCodeExchangeRejectReason


AuthorizationCodeExchangeResult: TypeAlias = Annotated[
    AuthorizationCodeExchanged | AuthorizationCodeExchangeRejected,
    Field(discriminator="kind"),
]
