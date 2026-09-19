from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.application.api_credential_values import ApiAccessToken
from gomazon_webasyst.contracts.api_credentials import (
    ApiAccessTokenResolveRejected,
    ApiAccessTokenResolved,
)
from gomazon_webasyst.contracts.enums import (
    ApiAccessTokenResolveRejectReason,
    OAuthRevokeAuthenticationKind,
)


@dataclass(slots=True, frozen=True)
class OAuthRevokeAuthenticated:
    kind: OAuthRevokeAuthenticationKind
    contact_id: int
    token: ApiAccessToken

    def __init__(self, contact_id: int, token: ApiAccessToken) -> None:
        object.__setattr__(self, "kind", OAuthRevokeAuthenticationKind.AUTHENTICATED)
        object.__setattr__(self, "contact_id", contact_id)
        object.__setattr__(self, "token", token)


@dataclass(slots=True, frozen=True)
class OAuthRevokeAuthenticationRejected:
    kind: OAuthRevokeAuthenticationKind
    reason: ApiAccessTokenResolveRejectReason

    def __init__(self, reason: ApiAccessTokenResolveRejectReason) -> None:
        object.__setattr__(self, "kind", OAuthRevokeAuthenticationKind.REJECTED)
        object.__setattr__(self, "reason", reason)


OAuthRevokeAuthenticationResult: TypeAlias = (
    OAuthRevokeAuthenticated | OAuthRevokeAuthenticationRejected
)


class OAuthRevokeAuthenticationFlow:
    def __init__(
        self,
        *,
        resolve_access_token,
        activity_service,
    ) -> None:
        self._resolve_access_token = resolve_access_token
        self._activity_service = activity_service

    async def authenticate(
        self,
        token: ApiAccessToken,
    ) -> OAuthRevokeAuthenticationResult:
        resolved = await self._resolve_access_token(token)
        if isinstance(resolved, ApiAccessTokenResolveRejected):
            return OAuthRevokeAuthenticationRejected(resolved.reason)
        if not isinstance(resolved, ApiAccessTokenResolved):
            raise AssertionError("unsupported api token resolution")

        await self._activity_service.touch_if_due(resolved.contact_id)
        return OAuthRevokeAuthenticated(
            contact_id=resolved.contact_id,
            token=resolved.access_token,
        )
