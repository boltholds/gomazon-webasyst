from gomazon_webasyst.application.app_values import AppId
from gomazon_webasyst.application.oauth_authorization.entities.consent_application import (
    OAuthConsentApplication,
)
from gomazon_webasyst.application.oauth_authorization.vo.client import (
    OAuthAppDisplayName,
    OAuthAppIconReference,
)
from gomazon_webasyst.application.ports.application_registry import (
    ApplicationEnabled,
    ApplicationRegistry,
)
from gomazon_webasyst.application.ports.oauth_consent_apps import (
    OAuthConsentApplicationMissing,
    OAuthConsentApplicationResolution,
    OAuthConsentApplicationResolved,
)


class RegistryBackedOAuthConsentAppCatalog:
    def __init__(self, registry: ApplicationRegistry) -> None:
        self._registry = registry

    def resolve(self, app_id: AppId) -> OAuthConsentApplicationResolution:
        resolution = self._registry.resolve_app(app_id)
        if not isinstance(resolution, ApplicationEnabled):
            return OAuthConsentApplicationMissing(app_id)

        descriptor = resolution.descriptor
        if not descriptor.icon:
            raise ValueError(
                f"enabled oauth consent application has no icon: {app_id.value}"
            )

        return OAuthConsentApplicationResolved(
            OAuthConsentApplication(
                app_id=descriptor.id,
                display_name=OAuthAppDisplayName(descriptor.name),
                icon=OAuthAppIconReference(descriptor.icon),
            )
        )
