from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.api_credential_values import ApiScope
from gomazon_webasyst.contracts.api_credentials import ApiTokenExpiry


@dataclass(slots=True, frozen=True)
class KeepAuthorizationCode:
    pass


@dataclass(slots=True, frozen=True)
class ConsumeAuthorizationCode:
    pass


AuthorizationCodeExchangeDisposition: TypeAlias = KeepAuthorizationCode | ConsumeAuthorizationCode


@dataclass(slots=True, frozen=True)
class ReuseApiToken:
    pass


@dataclass(slots=True, frozen=True)
class ReuseApiTokenWithScopeUpdate:
    scope: ApiScope


@dataclass(slots=True, frozen=True)
class CreateApiToken:
    expiry: ApiTokenExpiry


ExistingApiTokenIssuePlan: TypeAlias = ReuseApiToken | ReuseApiTokenWithScopeUpdate
ApiTokenIssuePlan: TypeAlias = ExistingApiTokenIssuePlan | CreateApiToken


class AuthorizationCodeLifetimePolicy(Protocol):
    def expires_at(self, now: datetime) -> datetime: ...


class AuthorizationCodeExchangePolicy(Protocol):
    def disposition(self) -> AuthorizationCodeExchangeDisposition: ...


class ApiTokenIssuePolicy(Protocol):
    def for_existing(
        self,
        current_scope: ApiScope,
        requested_scope: ApiScope,
    ) -> ExistingApiTokenIssuePlan: ...

    def for_missing(self) -> CreateApiToken: ...
