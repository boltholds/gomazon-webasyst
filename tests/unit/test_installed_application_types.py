from dataclasses import FrozenInstanceError

import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.application_registry.entities.installed_application import (
    InstalledApplication,
)
from gomazon_webasyst.application.application_registry.vo.capabilities import (
    ApplicationCapabilities,
    ApplicationCapabilityName,
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
from gomazon_webasyst.application.ports.installed_application_catalog import (
    InstalledApplicationMissing,
    InstalledApplicationResolved,
    InstalledApplicationSnapshot,
)
from gomazon_webasyst.contracts.enums import EnumStr, InstalledApplicationLookupKind


def _app(app_id: str = "shop", name: str = "Shop") -> InstalledApplication:
    return InstalledApplication(
        app_id=AppId(app_id),
        display_name=ApplicationDisplayName(name),
        icons=ApplicationIconSet(
            (ApplicationIcon(48, ApplicationIconReference(f"wa-apps/{app_id}/img/icon.svg")),)
        ),
        vendor=ApplicationVendor("webasyst"),
        version=ApplicationVersion("1.0.0"),
        capabilities=ApplicationCapabilities(
            frozenset(
                {
                    ApplicationCapabilityName("frontend"),
                    ApplicationCapabilityName("plugins"),
                }
            )
        ),
        header_items=ApplicationHeaderItems(()),
    )


def test_installed_application_has_stable_app_identity_and_is_frozen() -> None:
    app = _app()
    assert app.app_id == AppId("shop")
    assert hash(app)
    with pytest.raises(FrozenInstanceError):
        app.display_name = ApplicationDisplayName("Other")  # type: ignore[misc]


def test_metadata_value_objects_reject_empty_values() -> None:
    for value_type in (
        ApplicationDisplayName,
        ApplicationVendor,
        ApplicationVersion,
        ApplicationIconReference,
        ApplicationHeaderItemId,
        ApplicationCapabilityName,
    ):
        with pytest.raises(ValueError):
            value_type("")


def test_icon_requires_positive_size_and_icon_set_rejects_duplicate_sizes() -> None:
    ref = ApplicationIconReference("wa-apps/shop/img/icon.svg")
    with pytest.raises(ValueError):
        ApplicationIcon(0, ref)

    with pytest.raises(ValueError, match="duplicate"):
        ApplicationIconSet(
            (
                ApplicationIcon(48, ref),
                ApplicationIcon(48, ApplicationIconReference("other.svg")),
            )
        )


def test_capability_names_are_open_identifiers_not_closed_enum_members() -> None:
    custom = ApplicationCapabilityName("vendor_specific_capability")
    capabilities = ApplicationCapabilities(frozenset({custom}))
    assert custom in capabilities.values


def test_header_items_reject_duplicate_item_identity() -> None:
    item = ApplicationHeaderItem(
        item_id=ApplicationHeaderItemId("settings"),
        display_name=ApplicationDisplayName("Settings"),
        icons=ApplicationIconSet(()),
    )
    with pytest.raises(ValueError, match="duplicate"):
        ApplicationHeaderItems((item, item))


def test_lookup_result_kind_is_enumstr_and_explicit() -> None:
    app = _app()
    resolved = InstalledApplicationResolved(app)
    missing = InstalledApplicationMissing(AppId("crm"))

    assert issubclass(InstalledApplicationLookupKind, EnumStr)
    assert resolved.kind is InstalledApplicationLookupKind.RESOLVED
    assert resolved.application is app
    assert missing.kind is InstalledApplicationLookupKind.MISSING
    assert missing.app_id == AppId("crm")


def test_snapshot_preserves_order_and_rejects_duplicate_app_ids() -> None:
    shop = _app("shop", "Shop")
    blog = _app("blog", "Blog")
    snapshot = InstalledApplicationSnapshot((shop, blog))
    assert snapshot.applications == (shop, blog)

    with pytest.raises(ValueError, match="duplicate"):
        InstalledApplicationSnapshot((shop, _app("shop", "Other")))
