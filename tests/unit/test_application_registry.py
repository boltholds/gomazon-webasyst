import pytest

from gomazon_webasyst.application.app_values import AppId, PluginId, PluginRef
from gomazon_webasyst.application.application_registry import (
    ApplicationCatalog,
    InstallationManifest,
    InstalledApplication,
    StaticApplicationRegistry,
)
from gomazon_webasyst.application.ports.application_registry import (
    ApplicationDisabled,
    ApplicationEnabled,
    ApplicationUnknown,
    PluginDisabled,
    PluginEnabled,
    PluginListOwnerDisabled,
    PluginListOwnerUnknown,
    PluginListResolved,
    PluginOwnerDisabled,
    PluginUnknown,
)
from gomazon_webasyst.contracts.applications import (
    ApplicationCapabilities,
    ApplicationDescriptor,
    PluginDescriptor,
)


def _app(
    app_id: str,
    *,
    system: bool = False,
) -> ApplicationDescriptor:
    return ApplicationDescriptor(
        id=AppId(app_id),
        name=app_id.title(),
        capabilities=ApplicationCapabilities(system=system),
        framework_system=system,
    )


def _plugin(app_id: str, plugin_id: str) -> PluginDescriptor:
    return PluginDescriptor(
        ref=PluginRef(AppId(app_id), PluginId(plugin_id)),
        name=plugin_id.title(),
    )


def _catalog() -> ApplicationCatalog:
    return ApplicationCatalog(
        applications=(
            _app("blog"),
            _app("photos"),
            _app("webasyst", system=True),
        ),
        plugins=(
            _plugin("blog", "markdown"),
            _plugin("blog", "favorite"),
            _plugin("photos", "comments"),
        ),
    )


def _manifest() -> InstallationManifest:
    return InstallationManifest(
        apps=(
            InstalledApplication(
                AppId("blog"),
                (PluginId("markdown"),),
            ),
            InstalledApplication(AppId("webasyst")),
        )
    )


def _registry() -> StaticApplicationRegistry:
    return StaticApplicationRegistry(_catalog(), _manifest())


def test_registry_rejects_duplicate_catalog_application_ids() -> None:
    catalog = ApplicationCatalog(
        applications=(_app("blog"), _app("blog")),
    )

    with pytest.raises(ValueError, match="duplicate application id"):
        StaticApplicationRegistry(catalog, InstallationManifest(()))


def test_registry_rejects_duplicate_catalog_plugin_refs() -> None:
    plugin = _plugin("blog", "markdown")
    catalog = ApplicationCatalog(
        applications=(_app("blog"),),
        plugins=(plugin, plugin),
    )

    with pytest.raises(ValueError, match="duplicate plugin ref"):
        StaticApplicationRegistry(catalog, InstallationManifest(()))


def test_registry_rejects_plugin_with_unknown_catalog_owner() -> None:
    catalog = ApplicationCatalog(
        applications=(_app("blog"),),
        plugins=(_plugin("photos", "comments"),),
    )

    with pytest.raises(ValueError, match="plugin owner is absent"):
        StaticApplicationRegistry(catalog, InstallationManifest(()))


def test_registry_rejects_duplicate_installed_applications() -> None:
    manifest = InstallationManifest(
        (
            InstalledApplication(AppId("blog")),
            InstalledApplication(AppId("blog")),
            InstalledApplication(AppId("webasyst")),
        )
    )

    with pytest.raises(ValueError, match="duplicate installed application"):
        StaticApplicationRegistry(_catalog(), manifest)


def test_registry_rejects_unknown_installed_application() -> None:
    manifest = InstallationManifest(
        (
            InstalledApplication(AppId("missing")),
            InstalledApplication(AppId("webasyst")),
        )
    )

    with pytest.raises(ValueError, match="unknown installed application"):
        StaticApplicationRegistry(_catalog(), manifest)


def test_registry_rejects_duplicate_installed_plugins() -> None:
    manifest = InstallationManifest(
        (
            InstalledApplication(
                AppId("blog"),
                (PluginId("markdown"), PluginId("markdown")),
            ),
            InstalledApplication(AppId("webasyst")),
        )
    )

    with pytest.raises(ValueError, match="duplicate installed plugin"):
        StaticApplicationRegistry(_catalog(), manifest)


def test_registry_rejects_unknown_or_wrongly_owned_plugin() -> None:
    manifest = InstallationManifest(
        (
            InstalledApplication(
                AppId("photos"),
                (PluginId("markdown"),),
            ),
            InstalledApplication(AppId("webasyst")),
        )
    )

    with pytest.raises(ValueError, match="unknown or wrongly-owned"):
        StaticApplicationRegistry(_catalog(), manifest)


def test_registry_requires_catalog_system_applications_in_manifest() -> None:
    manifest = InstallationManifest(
        (InstalledApplication(AppId("blog")),)
    )

    with pytest.raises(ValueError, match="required system application"):
        StaticApplicationRegistry(_catalog(), manifest)


def test_resolve_app_distinguishes_enabled_disabled_and_unknown() -> None:
    registry = _registry()

    assert isinstance(registry.resolve_app(AppId("blog")), ApplicationEnabled)
    assert isinstance(registry.resolve_app(AppId("photos")), ApplicationDisabled)
    assert isinstance(registry.resolve_app(AppId("missing")), ApplicationUnknown)


def test_resolve_plugin_distinguishes_all_availability_states() -> None:
    registry = _registry()

    assert isinstance(
        registry.resolve_plugin(
            PluginRef(AppId("blog"), PluginId("markdown"))
        ),
        PluginEnabled,
    )
    assert isinstance(
        registry.resolve_plugin(
            PluginRef(AppId("blog"), PluginId("favorite"))
        ),
        PluginDisabled,
    )
    assert isinstance(
        registry.resolve_plugin(
            PluginRef(AppId("photos"), PluginId("comments"))
        ),
        PluginOwnerDisabled,
    )
    assert isinstance(
        registry.resolve_plugin(
            PluginRef(AppId("blog"), PluginId("missing"))
        ),
        PluginUnknown,
    )


def test_application_lists_preserve_manifest_and_system_semantics() -> None:
    registry = _registry()

    assert tuple(
        descriptor.id.value for descriptor in registry.list_catalog_apps()
    ) == ("blog", "photos", "webasyst")
    assert tuple(
        descriptor.id.value for descriptor in registry.list_enabled_apps()
    ) == ("blog",)
    assert tuple(
        descriptor.id.value
        for descriptor in registry.list_enabled_apps_including_system()
    ) == ("blog", "webasyst")


def test_plugin_lists_keep_catalog_and_manifest_order_separate() -> None:
    registry = _registry()

    all_plugins = registry.list_plugins(AppId("blog"))
    assert isinstance(all_plugins, PluginListResolved)
    assert tuple(
        descriptor.ref.plugin_id.value
        for descriptor in all_plugins.plugins
    ) == ("markdown", "favorite")

    enabled_plugins = registry.list_enabled_plugins(AppId("blog"))
    assert isinstance(enabled_plugins, PluginListResolved)
    assert tuple(
        descriptor.ref.plugin_id.value
        for descriptor in enabled_plugins.plugins
    ) == ("markdown",)


def test_plugin_list_states_are_explicit_for_disabled_and_unknown_owner() -> None:
    registry = _registry()

    assert isinstance(
        registry.list_enabled_plugins(AppId("photos")),
        PluginListOwnerDisabled,
    )
    assert isinstance(
        registry.list_enabled_plugins(AppId("missing")),
        PluginListOwnerUnknown,
    )
