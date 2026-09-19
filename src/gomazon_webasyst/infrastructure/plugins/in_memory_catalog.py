from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.plugins.entities.installed_plugin import InstalledPlugin
from gomazon_webasyst.application.plugins.vo.identity import PluginKey
from gomazon_webasyst.application.ports.installed_plugin_catalog import (
    InstalledPluginMissing,
    InstalledPluginResolution,
    InstalledPluginResolved,
    InstalledPluginSnapshot,
)


class InMemoryInstalledPluginCatalog:
    def __init__(self, plugins: tuple[InstalledPlugin, ...]) -> None:
        by_key: dict[PluginKey, InstalledPlugin] = {}
        by_app: dict[AppId, list[InstalledPlugin]] = {}
        for plugin in plugins:
            if plugin.key in by_key:
                raise ValueError(
                    "duplicate installed plugin key: "
                    f"{plugin.key.app_id.value}.{plugin.key.plugin_id.value}"
                )
            by_key[plugin.key] = plugin
            by_app.setdefault(plugin.key.app_id, []).append(plugin)
        self._by_key = by_key
        self._by_app = {
            app_id: tuple(values)
            for app_id, values in by_app.items()
        }

    async def resolve(self, key: PluginKey) -> InstalledPluginResolution:
        if key not in self._by_key:
            return InstalledPluginMissing(key)
        return InstalledPluginResolved(self._by_key[key])

    async def for_application(
        self,
        app_id: AppId,
    ) -> InstalledPluginSnapshot:
        return InstalledPluginSnapshot(
            app_id=app_id,
            plugins=self._by_app.get(app_id, ()),
        )
