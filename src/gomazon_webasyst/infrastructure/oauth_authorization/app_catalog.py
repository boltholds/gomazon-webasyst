from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.oauth_authorization.entities.consent_application import (
    OAuthConsentApplication,
)
from gomazon_webasyst.application.ports.oauth_consent_apps import (
    OAuthConsentApplicationMissing,
    OAuthConsentApplicationResolution,
    OAuthConsentApplicationResolved,
)


class InMemoryOAuthConsentAppCatalog:
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

    def resolve(self, app_id: AppId) -> OAuthConsentApplicationResolution:
        if app_id not in self._applications:
            return OAuthConsentApplicationMissing(app_id)
        return OAuthConsentApplicationResolved(self._applications[app_id])
