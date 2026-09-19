from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.oauth_authorization.entities.consent_application import (
    OAuthConsentApplication,
)
from gomazon_webasyst.application.ports.installed_application_catalog import (
    InstalledApplicationCatalog,
    InstalledApplicationMissing,
    InstalledApplicationResolved,
)
from gomazon_webasyst.application.ports.oauth_consent_apps import (
    OAuthConsentApplicationMissing,
    OAuthConsentApplicationResolution,
    OAuthConsentApplicationResolved,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.consent_application_projector import (
    LegacyOAuthConsentApplicationProjector,
)


class InstalledApplicationOAuthConsentAppCatalog:
    def __init__(
        self,
        installed_applications: InstalledApplicationCatalog,
        projector: LegacyOAuthConsentApplicationProjector,
    ) -> None:
        self._installed_applications = installed_applications
        self._projector = projector

    async def resolve(
        self,
        app_id: AppId,
    ) -> OAuthConsentApplicationResolution:
        resolved = await self._installed_applications.resolve(app_id)
        if isinstance(resolved, InstalledApplicationMissing):
            return OAuthConsentApplicationMissing(app_id)
        if not isinstance(resolved, InstalledApplicationResolved):
            raise AssertionError(
                "unsupported installed application resolution"
            )
        return OAuthConsentApplicationResolved(
            self._projector.project(resolved.application)
        )


class InMemoryOAuthConsentAppCatalog:
    """OAuth-specific test fake; production uses the canonical app projection."""

    def __init__(
        self,
        applications: tuple[OAuthConsentApplication, ...],
    ) -> None:
        by_id: dict[AppId, OAuthConsentApplication] = {}
        for application in applications:
            if application.app_id in by_id:
                raise ValueError(
                    f"duplicate oauth consent app id: {application.app_id.value}"
                )
            by_id[application.app_id] = application
        self._applications = by_id

    async def resolve(
        self,
        app_id: AppId,
    ) -> OAuthConsentApplicationResolution:
        if app_id not in self._applications:
            return OAuthConsentApplicationMissing(app_id)
        return OAuthConsentApplicationResolved(self._applications[app_id])
