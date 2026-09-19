from gomazon_webasyst.contracts.dispatch import (
    HandlerKey,
    HandlerMissing,
    HandlerRegistered,
    HandlerRegistryLookup,
    ModuleHandlerKey,
)


class InMemoryHandlerRegistry:
    def __init__(self) -> None:
        self._controllers: dict[HandlerKey, str] = {}
        self._actions: dict[HandlerKey, str] = {}
        self._multi_actions: dict[ModuleHandlerKey, str] = {}

    def register_controller(self, key: HandlerKey, handler_id: str) -> None:
        self._controllers[key] = handler_id

    def register_action(self, key: HandlerKey, handler_id: str) -> None:
        self._actions[key] = handler_id

    def register_actions(self, key: ModuleHandlerKey, handler_id: str) -> None:
        self._multi_actions[key] = handler_id

    def controller_id(self, key: HandlerKey) -> HandlerRegistryLookup:
        if key not in self._controllers:
            return HandlerMissing()
        return HandlerRegistered(handler_id=self._controllers[key])

    def action_id(self, key: HandlerKey) -> HandlerRegistryLookup:
        if key not in self._actions:
            return HandlerMissing()
        return HandlerRegistered(handler_id=self._actions[key])

    def actions_id(self, key: ModuleHandlerKey) -> HandlerRegistryLookup:
        if key not in self._multi_actions:
            return HandlerMissing()
        return HandlerRegistered(handler_id=self._multi_actions[key])
