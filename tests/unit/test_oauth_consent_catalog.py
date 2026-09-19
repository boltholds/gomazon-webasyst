import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.application_registry.entities.installed_application import (
    InstalledApplication,
)
from gomazon_webasyst.application.application_registry.vo.capabilities import (
    ApplicationCapabilities,
)
from gomazon_webasyst.application.application_registry.vo.header_items import (
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
from gomazon_webasyst.application.ports.oauth_consent_apps import (
    OAuthConsentApplicationMissing,
    OAuthConsentApplicationResolved,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.consent_application_projector import (
    LegacyOAuthConsentApplicationProjector,
)
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
)
from gomazon_webasyst.infrastructure.oauth_authorization.app_catalog import (
    InMemoryOAuthConsentAppCatalog,
    InstalledApplicationOAuthConsentAppCatalog,
)
from gomazon_webasyst.application.oauth_authorization.entities.consent_application import (
    OAuthConsentApplication,
)
from gomazon_webasyst.application.oauth_authorization.vo.client import (
    OAuthAppDisplayName,
    OAuthAppIconReference,
)


def installed_app(app_id: str, name: str) -> InstalledApplication:
    return InstalledApplication(
        app_id=AppId(app_id),
        display_name=ApplicationDisplayName(name),
        icons=ApplicationIconSet(
            (
                ApplicationIcon(
                    48,
                    ApplicationIconReference(
                        f"wa-apps/{app_id}/img/icon48.png"
                    ),
                ),
            )
        ),
        vendor=ApplicationVendor("webasyst"),
        version=ApplicationVersion("1.0.0"),
        capabilities=ApplicationCapabilities(frozenset()),
        header_items=ApplicationHeaderItems(()),
    )


@pytest.mark.asyncio
async def test_catalog_projects_canonical_registered_entity_and_reports_missing() -> None:
    shop = installed_app("shop", "Shop")
    canonical = InMemoryInstalledApplicationCatalog((shop,))
    catalog = InstalledApplicationOAuthConsentAppCatalog(
        canonical,
        LegacyOAuthConsentApplicationProjector(),
    )

    resolved = await catalog.resolve(AppId("shop"))
    missing = await catalog.resolve(AppId("crm"))

    assert isinstance(resolved, OAuthConsentApplicationResolved)
    assert resolved.application.app_id == AppId("shop")
    assert resolved.application.display_name.value == "Shop"
    assert isinstance(missing, OAuthConsentApplicationMissing)
    assert missing.app_id == AppId("crm")


@pytest.mark.asyncio
async def test_in_memory_oauth_catalog_remains_async_test_fake() -> None:
    app = OAuthConsentApplication(
        app_id=AppId("shop"),
        display_name=OAuthAppDisplayName("Shop"),
        icon=OAuthAppIconReference("/shop.png"),
    )
    catalog = InMemoryOAuthConsentAppCatalog((app,))

    resolved = await catalog.resolve(AppId("shop"))

    assert isinstance(resolved, OAuthConsentApplicationResolved)
    assert resolved.application is app


def test_in_memory_oauth_catalog_rejects_duplicate_app_identity() -> None:
    first = OAuthConsentApplication(
        app_id=AppId("shop"),
        display_name=OAuthAppDisplayName("Shop"),
        icon=OAuthAppIconReference("/shop.png"),
    )
    second = OAuthConsentApplication(
        app_id=AppId("shop"),
        display_name=OAuthAppDisplayName("Other"),
        icon=OAuthAppIconReference("/other.png"),
    )

    with pytest.raises(ValueError, match="duplicate"):
        InMemoryOAuthConsentAppCatalog((first, second))
