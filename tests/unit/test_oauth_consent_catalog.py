import pytest

from gomazon_webasyst.application.app_values import AppId
from gomazon_webasyst.application.application_registry import (
    ApplicationCatalog,
    InstallationManifest,
    InstalledApplication,
    StaticApplicationRegistry,
)
from gomazon_webasyst.application.oauth_authorization.services.app_catalog import (
    RegistryBackedOAuthConsentAppCatalog,
)
from gomazon_webasyst.application.ports.oauth_consent_apps import (
    OAuthConsentApplicationMissing,
    OAuthConsentApplicationResolved,
)
from gomazon_webasyst.contracts.applications import ApplicationDescriptor


def _registry(
    *,
    enabled: tuple[str, ...] = ("shop",),
    shop_icon: str = "/shop.png",
) -> StaticApplicationRegistry:
    return StaticApplicationRegistry(
        ApplicationCatalog(
            applications=(
                ApplicationDescriptor(
                    id=AppId("shop"),
                    name="Shop",
                    icon=shop_icon,
                ),
                ApplicationDescriptor(
                    id=AppId("crm"),
                    name="CRM",
                    icon="/crm.png",
                ),
            ),
        ),
        InstallationManifest(
            apps=tuple(
                InstalledApplication(AppId(app_id))
                for app_id in enabled
            )
        ),
    )


def test_catalog_projects_enabled_registry_application() -> None:
    registry = _registry()
    catalog = RegistryBackedOAuthConsentAppCatalog(registry)

    resolved = catalog.resolve(AppId("shop"))

    assert isinstance(resolved, OAuthConsentApplicationResolved)
    assert resolved.application.app_id == AppId("shop")
    assert resolved.application.display_name.value == "Shop"
    assert resolved.application.icon.value == "/shop.png"


def test_catalog_hides_disabled_and_unknown_applications() -> None:
    catalog = RegistryBackedOAuthConsentAppCatalog(_registry())

    disabled = catalog.resolve(AppId("crm"))
    unknown = catalog.resolve(AppId("missing"))

    assert isinstance(disabled, OAuthConsentApplicationMissing)
    assert disabled.app_id == AppId("crm")
    assert isinstance(unknown, OAuthConsentApplicationMissing)
    assert unknown.app_id == AppId("missing")


def test_enabled_consent_application_requires_real_icon_metadata() -> None:
    catalog = RegistryBackedOAuthConsentAppCatalog(
        _registry(shop_icon="")
    )

    with pytest.raises(ValueError, match="has no icon"):
        catalog.resolve(AppId("shop"))
