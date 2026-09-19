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
    ApplicationIconSet,
)
from gomazon_webasyst.application.application_registry.vo.metadata import (
    ApplicationDisplayName,
    ApplicationVendor,
    ApplicationVersion,
)
from gomazon_webasyst.application.ports.installed_application_catalog import (
    InstalledApplicationMissing,
    InstalledApplicationResolved,
)
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
)


def _app(app_id: str, name: str) -> InstalledApplication:
    return InstalledApplication(
        app_id=AppId(app_id),
        display_name=ApplicationDisplayName(name),
        icons=ApplicationIconSet(()),
        vendor=ApplicationVendor("webasyst"),
        version=ApplicationVersion("1.0.0"),
        capabilities=ApplicationCapabilities(frozenset()),
        header_items=ApplicationHeaderItems(()),
    )


@pytest.mark.asyncio
async def test_catalog_resolves_registered_application_and_reports_missing() -> None:
    shop = _app("shop", "Shop")
    catalog = InMemoryInstalledApplicationCatalog((shop,))

    resolved = await catalog.resolve(AppId("shop"))
    missing = await catalog.resolve(AppId("crm"))

    assert isinstance(resolved, InstalledApplicationResolved)
    assert resolved.application is shop
    assert isinstance(missing, InstalledApplicationMissing)
    assert missing.app_id == AppId("crm")


@pytest.mark.asyncio
async def test_snapshot_preserves_constructor_order() -> None:
    shop = _app("shop", "Shop")
    blog = _app("blog", "Blog")
    catalog = InMemoryInstalledApplicationCatalog((shop, blog))

    snapshot = await catalog.snapshot()

    assert snapshot.applications == (shop, blog)


def test_catalog_rejects_duplicate_application_identity() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        InMemoryInstalledApplicationCatalog(
            (_app("shop", "Shop"), _app("shop", "Other"))
        )


@pytest.mark.asyncio
async def test_snapshot_is_immutable_from_caller_perspective() -> None:
    shop = _app("shop", "Shop")
    catalog = InMemoryInstalledApplicationCatalog((shop,))

    snapshot = await catalog.snapshot()

    with pytest.raises(TypeError):
        snapshot.applications[0] = _app("blog", "Blog")  # type: ignore[index]
