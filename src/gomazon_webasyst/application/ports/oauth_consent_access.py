from dataclasses import dataclass
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.enums import OAuthConsentAccessKind


@dataclass(slots=True, frozen=True)
class OAuthConsentAccessGranted:
    kind: OAuthConsentAccessKind
    app_id: AppId

    def __init__(self, app_id: AppId) -> None:
        object.__setattr__(self, "kind", OAuthConsentAccessKind.GRANTED)
        object.__setattr__(self, "app_id", app_id)


@dataclass(slots=True, frozen=True)
class OAuthConsentAccessDenied:
    kind: OAuthConsentAccessKind
    app_id: AppId

    def __init__(self, app_id: AppId) -> None:
        object.__setattr__(self, "kind", OAuthConsentAccessKind.DENIED)
        object.__setattr__(self, "app_id", app_id)


OAuthConsentAccessDecision: TypeAlias = (
    OAuthConsentAccessGranted | OAuthConsentAccessDenied
)


class OAuthConsentAccessPolicy(Protocol):
    async def authorize(
        self,
        subject: AuthenticatedSubject,
        app_id: AppId,
    ) -> OAuthConsentAccessDecision: ...
