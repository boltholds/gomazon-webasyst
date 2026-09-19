from dataclasses import dataclass

from gomazon_webasyst.application.plugins.vo.capabilities import PluginCapabilities
from gomazon_webasyst.application.plugins.vo.handlers import PluginHandlerDeclarations
from gomazon_webasyst.application.plugins.vo.identity import PluginKey
from gomazon_webasyst.application.plugins.vo.metadata import (
    PluginDisplayName,
    PluginImageState,
    PluginVendor,
    PluginVersion,
)


@dataclass(slots=True, frozen=True)
class InstalledPlugin:
    key: PluginKey
    display_name: PluginDisplayName
    version: PluginVersion
    vendor: PluginVendor
    image: PluginImageState
    capabilities: PluginCapabilities
    handler_declarations: PluginHandlerDeclarations
