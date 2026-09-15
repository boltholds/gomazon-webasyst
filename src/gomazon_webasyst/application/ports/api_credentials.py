from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.api_credential_values import (
    ApiAccessToken,
    ApiClientId,
    ApiScope,
    AuthorizationCode,
)
from gomazon_webasyst.contracts.api_credentials import (
    ApiTokenResolution,
    StoredApiAccessToken,
    StoredAuthorizationCode,
)


@dataclass(slots=True, frozen=True)
class AuthorizationCodeStored:
    record: StoredAuthorizationCode


@dataclass(slots=True, frozen=True)
class AuthorizationCodeCreateCollision:
    code: AuthorizationCode


AuthorizationCodeCreateResult: TypeAlias = AuthorizationCodeStored | AuthorizationCodeCreateCollision


@dataclass(slots=True, frozen=True)
class AuthorizationCodeFound:
    record: StoredAuthorizationCode


@dataclass(slots=True, frozen=True)
class AuthorizationCodeMissing:
    code: AuthorizationCode


AuthorizationCodeResolution: TypeAlias = AuthorizationCodeFound | AuthorizationCodeMissing


@dataclass(slots=True, frozen=True)
class AuthorizationCodeDeleted:
    code: AuthorizationCode


@dataclass(slots=True, frozen=True)
class AuthorizationCodeAlreadyMissing:
    code: AuthorizationCode


AuthorizationCodeDeleteResult: TypeAlias = AuthorizationCodeDeleted | AuthorizationCodeAlreadyMissing


@dataclass(slots=True, frozen=True)
class ApiTokenForSubjectClientFound:
    record: StoredApiAccessToken


@dataclass(slots=True, frozen=True)
class ApiTokenForSubjectClientMissing:
    contact_id: int
    client_id: ApiClientId


ApiTokenSubjectClientLookup: TypeAlias = (
    ApiTokenForSubjectClientFound | ApiTokenForSubjectClientMissing
)


@dataclass(slots=True, frozen=True)
class ApiTokenStored:
    record: StoredApiAccessToken


@dataclass(slots=True, frozen=True)
class ApiTokenSubjectClientCollision:
    contact_id: int
    client_id: ApiClientId


@dataclass(slots=True, frozen=True)
class ApiTokenValueCollision:
    token: ApiAccessToken


ApiTokenCreateResult: TypeAlias = (
    ApiTokenStored | ApiTokenSubjectClientCollision | ApiTokenValueCollision
)


@dataclass(slots=True, frozen=True)
class ApiTokenScopeUpdated:
    token: ApiAccessToken
    scope: ApiScope


@dataclass(slots=True, frozen=True)
class ApiTokenScopeUpdateMissing:
    token: ApiAccessToken


ApiTokenScopeUpdateResult: TypeAlias = ApiTokenScopeUpdated | ApiTokenScopeUpdateMissing


@dataclass(slots=True, frozen=True)
class ApiTokenTouched:
    token: ApiAccessToken
    at: datetime


@dataclass(slots=True, frozen=True)
class ApiTokenTouchMissing:
    token: ApiAccessToken


ApiTokenTouchResult: TypeAlias = ApiTokenTouched | ApiTokenTouchMissing


@dataclass(slots=True, frozen=True)
class ApiTokenRevoked:
    token: ApiAccessToken


@dataclass(slots=True, frozen=True)
class ApiTokenAlreadyMissing:
    token: ApiAccessToken


ApiTokenRevocationResult: TypeAlias = ApiTokenRevoked | ApiTokenAlreadyMissing


class AuthorizationCodeRepository(Protocol):
    async def create(self, record: StoredAuthorizationCode) -> AuthorizationCodeCreateResult: ...

    async def resolve(self, code: AuthorizationCode) -> AuthorizationCodeResolution: ...

    async def delete(self, code: AuthorizationCode) -> AuthorizationCodeDeleteResult: ...


class ApiTokenRepository(Protocol):
    async def resolve(self, token: ApiAccessToken) -> ApiTokenResolution: ...

    async def find_for_subject_client(
        self,
        contact_id: int,
        client_id: ApiClientId,
    ) -> ApiTokenSubjectClientLookup: ...

    async def create(self, record: StoredApiAccessToken) -> ApiTokenCreateResult: ...

    async def update_scope(
        self,
        token: ApiAccessToken,
        scope: ApiScope,
    ) -> ApiTokenScopeUpdateResult: ...

    async def touch_last_use(
        self,
        token: ApiAccessToken,
        at: datetime,
    ) -> ApiTokenTouchResult: ...

    async def revoke(self, token: ApiAccessToken) -> ApiTokenRevocationResult: ...
