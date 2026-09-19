from typing import Protocol

from gomazon_webasyst.contracts.dispatch import (
    HandlerKey,
    HandlerRegistryLookup,
    ModuleHandlerKey,
)


class HandlerRegistry(Protocol):
    def controller_id(self, key: HandlerKey) -> HandlerRegistryLookup: ...

    def action_id(self, key: HandlerKey) -> HandlerRegistryLookup: ...

    def actions_id(self, key: ModuleHandlerKey) -> HandlerRegistryLookup: ...
