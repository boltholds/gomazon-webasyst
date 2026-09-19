from dataclasses import dataclass

from gomazon_webasyst.application.api_execution.entities.method_definition import (
    ApiMethodDefinition,
)
from gomazon_webasyst.application.events.entities.handler_definition import (
    EventHandlerDefinition,
)
from gomazon_webasyst.application.plugins.vo.identity import PluginKey
from gomazon_webasyst.application.runtime.vo.dispatch import (
    DispatchRuntimeDefinition,
)


@dataclass(slots=True, frozen=True)
class PluginRuntimeModule:
    key: PluginKey
    dispatch_handlers: tuple[DispatchRuntimeDefinition, ...]
    api_methods: tuple[ApiMethodDefinition, ...]
    event_handlers: tuple[EventHandlerDefinition, ...]

    def __post_init__(self) -> None:
        foreign_api = [
            definition.target
            for definition in self.api_methods
            if definition.target.app_id != self.key.app_id
        ]
        if foreign_api:
            raise ValueError("plugin runtime API method belongs to another application")
