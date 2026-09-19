from dataclasses import dataclass

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_execution.entities.method_definition import (
    ApiMethodDefinition,
)
from gomazon_webasyst.application.events.entities.handler_definition import (
    EventHandlerDefinition,
)
from gomazon_webasyst.application.runtime.entities.plugin_module import (
    PluginRuntimeModule,
)
from gomazon_webasyst.application.runtime.vo.dispatch import (
    DispatchRuntimeDefinition,
)


@dataclass(slots=True, frozen=True)
class ApplicationRuntimeModule:
    app_id: AppId
    dispatch_handlers: tuple[DispatchRuntimeDefinition, ...]
    api_methods: tuple[ApiMethodDefinition, ...]
    event_handlers: tuple[EventHandlerDefinition, ...]
    plugins: tuple[PluginRuntimeModule, ...]

    def __post_init__(self) -> None:
        foreign_api = [
            definition.target
            for definition in self.api_methods
            if definition.target.app_id != self.app_id
        ]
        if foreign_api:
            raise ValueError("application runtime API method belongs to another application")
        if any(plugin.key.app_id != self.app_id for plugin in self.plugins):
            raise ValueError("application runtime contains foreign plugin module")
        plugin_keys = [plugin.key for plugin in self.plugins]
        if len(plugin_keys) != len(set(plugin_keys)):
            raise ValueError("duplicate plugin runtime module")
