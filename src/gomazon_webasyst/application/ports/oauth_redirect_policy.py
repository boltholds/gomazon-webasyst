from dataclasses import dataclass
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.api_credential_values import ApiClientId
from gomazon_webasyst.application.oauth_authorization.vo.authorization import (
    OAuthRedirectTarget,
)


@dataclass(slots=True, frozen=True)
class OAuthRedirectAccepted:
    target: OAuthRedirectTarget


@dataclass(slots=True, frozen=True)
class OAuthRedirectRejected:
    reason: str


OAuthRedirectDecision: TypeAlias = OAuthRedirectAccepted | OAuthRedirectRejected


class OAuthRedirectPolicy(Protocol):
    def validate(
        self,
        client_id: ApiClientId,
        redirect_target: OAuthRedirectTarget,
    ) -> OAuthRedirectDecision: ...
