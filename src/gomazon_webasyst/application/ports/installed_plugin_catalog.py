from dataclasses import dataclass, field
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.plugins.entities.installed_plugin import InstalledPlugin
from gomazon_webasyst.application.plugins.vo.identity import PluginKey
from gomazon_webasyst.contracts.enums import InstalledPluginLookupKind


@dataclass(slots=True, frozen=True)
class InstalledPluginResolved:
    plugin: InstalledPlugin
    kind: InstalledPluginLookupKind = field(
        init=False,
        default=InstalledPluginLookupKind.RESOLVED,
    )


@dataclass(slots=True, frozen=True)
class InstalledPluginMissing:
    key: PluginKey
    kind: InstalledPluginLookupKind = field(
        init=False,
        default=InstalledPluginLookupKind.MISSING,
    )


InstalledPluginResolution: TypeAlias = InstalledPluginResolved | InstalledPluginMissing


@dataclass(slots=True, frozen=True)
class InstalledPluginSnapshot:
    app_id: AppId
    plugins: tuple[InstalledPlugin, ...]

    def __post_init__(self) -> None:
        keys = [plugin.key for plugin in self.plugins]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate installed plugin key")
        if any(plugin.key.app_id != self.app_id for plugin in self.plugins):
            raise ValueError("installed plugin snapshot contains foreign application")


class InstalledPluginCatalog(Protocol):
    async def resolve(self, key: PluginKey) -> InstalledPluginResolution: ...

    async def for_application(self, app_id: AppId) -> InstalledPluginSnapshot: ...
