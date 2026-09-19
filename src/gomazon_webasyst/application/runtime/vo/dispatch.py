from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.application.plugins.vo.identity import PluginKey
from gomazon_webasyst.contracts.dispatch import HandlerKey, ModuleHandlerKey


@dataclass(slots=True, frozen=True)
class DispatchHandlerId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("dispatch handler id must not be empty")


@dataclass(slots=True, frozen=True)
class ControllerDispatchDefinition:
    key: HandlerKey
    handler_id: DispatchHandlerId


@dataclass(slots=True, frozen=True)
class ActionDispatchDefinition:
    key: HandlerKey
    handler_id: DispatchHandlerId


@dataclass(slots=True, frozen=True)
class MultiActionDispatchDefinition:
    key: ModuleHandlerKey
    handler_id: DispatchHandlerId


@dataclass(slots=True, frozen=True)
class PluginAvailabilityDefinition:
    key: PluginKey


DispatchRuntimeDefinition: TypeAlias = (
    ControllerDispatchDefinition
    | ActionDispatchDefinition
    | MultiActionDispatchDefinition
    | PluginAvailabilityDefinition
)
