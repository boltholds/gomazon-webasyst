from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.application.api_credential_values import ApiScope
from gomazon_webasyst.application.oauth_authorization.entities.consent_application import (
    OAuthConsentApplication,
)
from gomazon_webasyst.application.oauth_authorization.vo.authorization import (
    OAuthRequestedScope,
)
from gomazon_webasyst.application.ports.oauth_consent_access import (
    OAuthConsentAccessDenied,
    OAuthConsentAccessGranted,
    OAuthConsentAccessPolicy,
)
from gomazon_webasyst.application.ports.oauth_consent_apps import (
    OAuthConsentAppCatalog,
    OAuthConsentApplicationMissing,
    OAuthConsentApplicationResolved,
)
from gomazon_webasyst.contracts.auth import AuthenticatedSubject


@dataclass(slots=True, frozen=True)
class OAuthEffectiveScopeResolved:
    scope: ApiScope
    applications: tuple[OAuthConsentApplication, ...]


@dataclass(slots=True, frozen=True)
class OAuthEffectiveScopeEmpty:
    pass


OAuthEffectiveScopeResult: TypeAlias = (
    OAuthEffectiveScopeResolved | OAuthEffectiveScopeEmpty
)


class OAuthConsentScopeService:
    def __init__(
        self,
        *,
        catalog: OAuthConsentAppCatalog,
        access: OAuthConsentAccessPolicy,
    ) -> None:
        self._catalog = catalog
        self._access = access

    async def filter(
        self,
        subject: AuthenticatedSubject,
        requested: OAuthRequestedScope,
    ) -> OAuthEffectiveScopeResult:
        app_ids = []
        applications = []

        for app_id in requested.apps:
            resolved = await self._catalog.resolve(app_id)
            if isinstance(resolved, OAuthConsentApplicationMissing):
                continue
            if not isinstance(resolved, OAuthConsentApplicationResolved):
                raise AssertionError("unsupported oauth consent app resolution")

            decision = await self._access.authorize(subject, app_id)
            if isinstance(decision, OAuthConsentAccessDenied):
                continue
            if not isinstance(decision, OAuthConsentAccessGranted):
                raise AssertionError("unsupported oauth consent access decision")

            app_ids.append(app_id)
            applications.append(resolved.application)

        if not app_ids:
            return OAuthEffectiveScopeEmpty()

        return OAuthEffectiveScopeResolved(
            scope=ApiScope(tuple(app_ids)),
            applications=tuple(applications),
        )
