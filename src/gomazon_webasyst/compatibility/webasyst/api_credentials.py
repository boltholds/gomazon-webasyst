from datetime import datetime, timedelta
from secrets import token_hex

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_credential_values import (
    ApiAccessToken,
    ApiScope,
    AuthorizationCode,
)
from gomazon_webasyst.application.ports.api_credential_policies import (
    CreateApiToken,
    KeepAuthorizationCode,
    ReuseApiToken,
    ReuseApiTokenWithScopeUpdate,
)
from gomazon_webasyst.contracts.api_credentials import ApiTokenNeverExpires


class WebasystApiCredentialGenerator:
    def authorization_code(self) -> AuthorizationCode:
        return AuthorizationCode(token_hex(16))

    def access_token(self) -> ApiAccessToken:
        return ApiAccessToken(token_hex(16))


class WebasystAuthorizationCodeLifetime:
    def expires_at(self, now: datetime) -> datetime:
        return now + timedelta(seconds=180)


class WebasystAuthorizationCodeExchangePolicy:
    def disposition(self) -> KeepAuthorizationCode:
        return KeepAuthorizationCode()


class WebasystApiTokenIssuePolicy:
    def for_existing(
        self,
        current_scope: ApiScope,
        requested_scope: ApiScope,
    ) -> ReuseApiToken | ReuseApiTokenWithScopeUpdate:
        if current_scope == requested_scope:
            return ReuseApiToken()
        return ReuseApiTokenWithScopeUpdate(scope=requested_scope)

    def for_missing(self) -> CreateApiToken:
        return CreateApiToken(expiry=ApiTokenNeverExpires())


class LegacyApiScopeCodec:
    def encode(self, scope: ApiScope) -> str:
        return ",".join(app.value for app in scope.apps)

    def decode(self, value: str) -> ApiScope:
        parts = value.split(",")
        if not parts or any(not part for part in parts):
            raise ValueError("legacy api scope contains an empty app id")
        return ApiScope(tuple(AppId(part) for part in parts))
