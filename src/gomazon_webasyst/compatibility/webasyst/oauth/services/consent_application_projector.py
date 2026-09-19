from gomazon_webasyst.application.application_registry.entities.installed_application import (
    InstalledApplication,
)
from gomazon_webasyst.application.application_registry.vo.icons import (
    ApplicationIconSet,
)
from gomazon_webasyst.application.oauth_authorization.entities.consent_application import (
    OAuthConsentApplication,
)
from gomazon_webasyst.application.oauth_authorization.vo.client import (
    OAuthAppDisplayName,
    OAuthAppIconReference,
)


class LegacyOAuthConsentProjectionError(ValueError):
    pass


class LegacyOAuthConsentApplicationProjector:
    def project(
        self,
        application: InstalledApplication,
    ) -> OAuthConsentApplication:
        icons = application.icons
        if application.app_id.value == "webasyst":
            icons = self._webasyst_settings_icons(application)

        icon = self._preferred_icon(icons)
        return OAuthConsentApplication(
            app_id=application.app_id,
            display_name=OAuthAppDisplayName(
                application.display_name.value
            ),
            icon=OAuthAppIconReference(icon),
        )

    @staticmethod
    def _webasyst_settings_icons(
        application: InstalledApplication,
    ) -> ApplicationIconSet:
        for item in application.header_items.items:
            if item.item_id.value == "settings":
                return item.icons
        raise LegacyOAuthConsentProjectionError(
            "webasyst consent metadata requires settings header item"
        )

    @staticmethod
    def _preferred_icon(icons: ApplicationIconSet) -> str:
        by_size = {icon.size: icon.reference.value for icon in icons.items}
        if 48 in by_size:
            return by_size[48]
        if by_size:
            return by_size[max(by_size)]
        raise LegacyOAuthConsentProjectionError(
            "oauth consent application requires an icon"
        )
