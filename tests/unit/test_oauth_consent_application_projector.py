from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.application_registry.entities.installed_application import (
    InstalledApplication,
)
from gomazon_webasyst.application.application_registry.vo.capabilities import (
    ApplicationCapabilities,
)
from gomazon_webasyst.application.application_registry.vo.header_items import (
    ApplicationHeaderItem,
    ApplicationHeaderItemId,
    ApplicationHeaderItems,
)
from gomazon_webasyst.application.application_registry.vo.icons import (
    ApplicationIcon,
    ApplicationIconReference,
    ApplicationIconSet,
)
from gomazon_webasyst.application.application_registry.vo.metadata import (
    ApplicationDisplayName,
    ApplicationVendor,
    ApplicationVersion,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.consent_application_projector import (
    LegacyOAuthConsentApplicationProjector,
)


def _application(
    app_id: str,
    *,
    name: str,
    icons: tuple[ApplicationIcon, ...],
    header_items: tuple[ApplicationHeaderItem, ...] = (),
) -> InstalledApplication:
    return InstalledApplication(
        app_id=AppId(app_id),
        display_name=ApplicationDisplayName(name),
        icons=ApplicationIconSet(icons),
        vendor=ApplicationVendor("webasyst"),
        version=ApplicationVersion("1.0.0"),
        capabilities=ApplicationCapabilities(frozenset()),
        header_items=ApplicationHeaderItems(header_items),
    )


def test_ordinary_oauth_projection_uses_locale_neutral_name_and_icon_48() -> None:
    app = _application(
        "shop",
        name="Shop",
        icons=(
            ApplicationIcon(16, ApplicationIconReference("wa-apps/shop/icon16.png")),
            ApplicationIcon(48, ApplicationIconReference("wa-apps/shop/icon48.png")),
        ),
    )

    projected = LegacyOAuthConsentApplicationProjector().project(app)

    assert projected.app_id == AppId("shop")
    assert projected.display_name.value == "Shop"
    assert projected.icon.value == "wa-apps/shop/icon48.png"


def test_webasyst_oauth_projection_uses_settings_header_icon() -> None:
    settings = ApplicationHeaderItem(
        item_id=ApplicationHeaderItemId("settings"),
        display_name=ApplicationDisplayName("Settings"),
        icons=ApplicationIconSet(
            (
                ApplicationIcon(
                    48,
                    ApplicationIconReference(
                        "wa-content/img/wa-settings/settings.svg"
                    ),
                ),
            )
        ),
    )
    app = _application(
        "webasyst",
        name="Webasyst",
        icons=(
            ApplicationIcon(
                48,
                ApplicationIconReference("wa-system/webasyst/img/main.svg"),
            ),
        ),
        header_items=(settings,),
    )

    projected = LegacyOAuthConsentApplicationProjector().project(app)

    assert projected.icon.value == "wa-content/img/wa-settings/settings.svg"
