from dataclasses import dataclass
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.app_values import AppId
from gomazon_webasyst.application.oauth_authorization.entities.consent_application import (
    OAuthConsentApplication,
)
from gomazon_webasyst.contracts.enums import OAuthConsentAppLookupKind


@dataclass(slots=True, frozen=True)
class OAuthConsentApplicationResolved:
    kind: OAuthConsentAppLookupKind
    application: OAuthConsentApplication

    def __init__(self, application: OAuthConsentApplication) -> None:
        object.__setattr__(self, "kind", OAuthConsentAppLookupKind.RESOLVED)
        object.__setattr__(self, "application", application)


@dataclass(slots=True, frozen=True)
class OAuthConsentApplicationMissing:
    kind: OAuthConsentAppLookupKind
    app_id: AppId

    def __init__(self, app_id: AppId) -> None:
        object.__setattr__(self, "kind", OAuthConsentAppLookupKind.MISSING)
        object.__setattr__(self, "app_id", app_id)


OAuthConsentApplicationResolution: TypeAlias = (
    OAuthConsentApplicationResolved | OAuthConsentApplicationMissing
)


class OAuthConsentAppCatalog(Protocol):
    def resolve(self, app_id: AppId) -> OAuthConsentApplicationResolution: ...
