from dataclasses import FrozenInstanceError

import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.plugins.entities.installed_plugin import InstalledPlugin
from gomazon_webasyst.application.plugins.vo.capabilities import (
    PluginCapabilities,
    PluginCapabilityName,
)
from gomazon_webasyst.application.plugins.vo.handlers import (
    PluginHandlerDeclaration,
    PluginHandlerDeclarations,
    PluginHandlerEventPattern,
    PluginHandlerMethodName,
)
from gomazon_webasyst.application.plugins.vo.identity import PluginId, PluginKey
from gomazon_webasyst.application.plugins.vo.metadata import (
    PluginDisplayName,
    PluginImageMissing,
    PluginImagePresent,
    PluginImageReference,
    PluginVendor,
    PluginVersion,
)
from gomazon_webasyst.application.ports.installed_plugin_catalog import (
    InstalledPluginMissing,
    InstalledPluginSnapshot,
)
from gomazon_webasyst.contracts.enums import InstalledPluginLookupKind, PluginImageKind


def _plugin(app: str = "site", plugin: str = "rublesign") -> InstalledPlugin:
    return InstalledPlugin(
        key=PluginKey(AppId(app), PluginId(plugin)),
        display_name=PluginDisplayName("Ruble"),
        version=PluginVersion("1.0.0"),
        vendor=PluginVendor("webasyst"),
        image=PluginImagePresent(PluginImageReference("wa-apps/site/plugins/rublesign/img.png")),
        capabilities=PluginCapabilities(
            frozenset({PluginCapabilityName("site_settings")})
        ),
        handler_declarations=PluginHandlerDeclarations(
            (
                PluginHandlerDeclaration(
                    source_app_id=AppId("webasyst"),
                    event_pattern=PluginHandlerEventPattern("backend_header"),
                    methods=(PluginHandlerMethodName("backendHeader"),),
                ),
            )
        ),
    )


def test_plugin_key_is_correlated_immutable_identity() -> None:
    key = PluginKey(AppId("site"), PluginId("rublesign"))
    assert key == PluginKey(AppId("site"), PluginId("rublesign"))
    assert {key}
    with pytest.raises(FrozenInstanceError):
        key.plugin_id = PluginId("other")  # type: ignore[misc]


@pytest.mark.parametrize("value", ["", "x" * 65])
def test_plugin_id_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        PluginId(value)


def test_plugin_image_uses_explicit_present_or_missing_state() -> None:
    present = PluginImagePresent(PluginImageReference("img/plugin.svg"))
    missing = PluginImageMissing()
    assert present.kind is PluginImageKind.PRESENT
    assert missing.kind is PluginImageKind.MISSING


def test_plugin_capability_names_are_open_values() -> None:
    capabilities = PluginCapabilities(
        frozenset(
            {
                PluginCapabilityName("frontend"),
                PluginCapabilityName("vendor_specific_future_flag"),
            }
        )
    )
    assert PluginCapabilityName("vendor_specific_future_flag") in capabilities.values


def test_handler_declaration_requires_at_least_one_method() -> None:
    with pytest.raises(ValueError):
        PluginHandlerDeclaration(
            source_app_id=AppId("site"),
            event_pattern=PluginHandlerEventPattern("frontend_head"),
            methods=(),
        )


def test_installed_plugin_is_frozen_and_carries_declarative_handlers_only() -> None:
    plugin = _plugin()
    assert plugin.key == PluginKey(AppId("site"), PluginId("rublesign"))
    assert plugin.handler_declarations.items[0].source_app_id == AppId("webasyst")
    with pytest.raises(FrozenInstanceError):
        plugin.display_name = PluginDisplayName("Other")  # type: ignore[misc]


def test_snapshot_rejects_duplicate_or_foreign_plugin_keys() -> None:
    plugin = _plugin()
    with pytest.raises(ValueError, match="duplicate"):
        InstalledPluginSnapshot(AppId("site"), (plugin, plugin))

    with pytest.raises(ValueError, match="foreign"):
        InstalledPluginSnapshot(AppId("blog"), (plugin,))


def test_plugin_lookup_miss_is_explicit_variant() -> None:
    key = PluginKey(AppId("site"), PluginId("missing"))
    missing = InstalledPluginMissing(key)
    assert missing.key == key
    assert missing.kind is InstalledPluginLookupKind.MISSING
