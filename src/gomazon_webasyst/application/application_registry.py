from dataclasses import dataclass

from gomazon_webasyst.application.app_values import AppId, PluginId, PluginRef
from gomazon_webasyst.application.ports.application_registry import (
    ApplicationDisabled,
    ApplicationEnabled,
    ApplicationResolution,
    ApplicationUnknown,
    PluginDisabled,
    PluginEnabled,
    PluginListOwnerDisabled,
    PluginListOwnerUnknown,
    PluginListResolved,
    PluginListResult,
    PluginOwnerDisabled,
    PluginResolution,
    PluginUnknown,
)
from gomazon_webasyst.contracts.applications import (
    ApplicationDescriptor,
    PluginDescriptor,
)


@dataclass(slots=True, frozen=True)
class ApplicationCatalog:
    applications: tuple[ApplicationDescriptor, ...]
    plugins: tuple[PluginDescriptor, ...] = ()


@dataclass(slots=True, frozen=True)
class InstalledApplication:
    app_id: AppId
    plugins: tuple[PluginId, ...] = ()


@dataclass(slots=True, frozen=True)
class InstallationManifest:
    apps: tuple[InstalledApplication, ...]


class StaticApplicationRegistry:
    def __init__(
        self,
        catalog: ApplicationCatalog,
        manifest: InstallationManifest,
    ) -> None:
        self._catalog = catalog
        self._manifest = manifest
        self._apps = self._index_applications(catalog.applications)
        self._plugins = self._index_plugins(catalog.plugins)
        self._plugins_by_app = self._group_plugins(catalog.plugins)
        self._installed = self._validate_manifest(manifest)
        self._validate_system_apps()

    @staticmethod
    def _index_applications(
        applications: tuple[ApplicationDescriptor, ...],
    ) -> dict[AppId, ApplicationDescriptor]:
        indexed: dict[AppId, ApplicationDescriptor] = {}
        for descriptor in applications:
            if descriptor.id in indexed:
                raise ValueError(
                    f"duplicate application id: {descriptor.id.value}"
                )
            indexed[descriptor.id] = descriptor
        return indexed

    def _index_plugins(
        self,
        plugins: tuple[PluginDescriptor, ...],
    ) -> dict[PluginRef, PluginDescriptor]:
        indexed: dict[PluginRef, PluginDescriptor] = {}
        for descriptor in plugins:
            if descriptor.ref in indexed:
                raise ValueError(
                    "duplicate plugin ref: "
                    f"{descriptor.ref.app_id.value}/"
                    f"{descriptor.ref.plugin_id.value}"
                )
            if descriptor.ref.app_id not in self._apps:
                raise ValueError(
                    "plugin owner is absent from application catalog: "
                    f"{descriptor.ref.app_id.value}/"
                    f"{descriptor.ref.plugin_id.value}"
                )
            indexed[descriptor.ref] = descriptor
        return indexed

    @staticmethod
    def _group_plugins(
        plugins: tuple[PluginDescriptor, ...],
    ) -> dict[AppId, tuple[PluginDescriptor, ...]]:
        grouped_lists: dict[AppId, list[PluginDescriptor]] = {}
        for descriptor in plugins:
            grouped_lists.setdefault(descriptor.ref.app_id, []).append(descriptor)
        return {
            app_id: tuple(descriptors)
            for app_id, descriptors in grouped_lists.items()
        }

    def _validate_manifest(
        self,
        manifest: InstallationManifest,
    ) -> dict[AppId, InstalledApplication]:
        installed: dict[AppId, InstalledApplication] = {}
        for entry in manifest.apps:
            if entry.app_id in installed:
                raise ValueError(
                    f"duplicate installed application: {entry.app_id.value}"
                )
            if entry.app_id not in self._apps:
                raise ValueError(
                    f"unknown installed application: {entry.app_id.value}"
                )

            plugin_ids: set[PluginId] = set()
            for plugin_id in entry.plugins:
                if plugin_id in plugin_ids:
                    raise ValueError(
                        "duplicate installed plugin: "
                        f"{entry.app_id.value}/{plugin_id.value}"
                    )
                plugin_ids.add(plugin_id)

                plugin_ref = PluginRef(entry.app_id, plugin_id)
                if plugin_ref not in self._plugins:
                    raise ValueError(
                        "unknown or wrongly-owned installed plugin: "
                        f"{entry.app_id.value}/{plugin_id.value}"
                    )

            installed[entry.app_id] = entry
        return installed

    def _validate_system_apps(self) -> None:
        for descriptor in self._catalog.applications:
            if (
                descriptor.capabilities.system
                and descriptor.id not in self._installed
            ):
                raise ValueError(
                    "required system application is not installed: "
                    f"{descriptor.id.value}"
                )

    def resolve_app(self, app_id: AppId) -> ApplicationResolution:
        if app_id not in self._apps:
            return ApplicationUnknown(app_id)
        descriptor = self._apps[app_id]
        if app_id in self._installed:
            return ApplicationEnabled(descriptor)
        return ApplicationDisabled(descriptor)

    def resolve_plugin(self, plugin_ref: PluginRef) -> PluginResolution:
        if plugin_ref not in self._plugins:
            return PluginUnknown(plugin_ref)
        descriptor = self._plugins[plugin_ref]

        owner = self._apps[plugin_ref.app_id]
        if plugin_ref.app_id not in self._installed:
            return PluginOwnerDisabled(descriptor, owner)
        installed_owner = self._installed[plugin_ref.app_id]

        if plugin_ref.plugin_id in installed_owner.plugins:
            return PluginEnabled(descriptor)
        return PluginDisabled(descriptor)

    def list_catalog_apps(self) -> tuple[ApplicationDescriptor, ...]:
        return self._catalog.applications

    def list_enabled_apps(self) -> tuple[ApplicationDescriptor, ...]:
        return tuple(
            self._apps[entry.app_id]
            for entry in self._manifest.apps
            if not self._apps[entry.app_id].capabilities.system
        )

    def list_enabled_apps_including_system(
        self,
    ) -> tuple[ApplicationDescriptor, ...]:
        return tuple(
            self._apps[entry.app_id]
            for entry in self._manifest.apps
        )

    def list_plugins(self, app_id: AppId) -> PluginListResult:
        if app_id not in self._apps:
            return PluginListOwnerUnknown(app_id)
        return PluginListResolved(
            app_id=app_id,
            plugins=self._plugins_by_app.get(app_id, ()),
        )

    def list_enabled_plugins(self, app_id: AppId) -> PluginListResult:
        if app_id not in self._apps:
            return PluginListOwnerUnknown(app_id)

        if app_id not in self._installed:
            return PluginListOwnerDisabled(app_id)
        installed = self._installed[app_id]

        return PluginListResolved(
            app_id=app_id,
            plugins=tuple(
                self._plugins[PluginRef(app_id, plugin_id)]
                for plugin_id in installed.plugins
            ),
        )
