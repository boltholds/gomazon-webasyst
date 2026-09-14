from gomazon_webasyst.contracts.dispatch import HandlerKey, ModuleHandlerKey


class InMemoryDispatchRegistry:
    def __init__(self) -> None:
        self._controllers: dict[HandlerKey, str] = {}
        self._actions: dict[HandlerKey, str] = {}
        self._multi_actions: dict[ModuleHandlerKey, str] = {}
        self._plugins: set[tuple[str, str]] = set()

    def register_controller(self, key: HandlerKey, handler_id: str) -> None:
        self._controllers[key] = handler_id

    def register_action(self, key: HandlerKey, handler_id: str) -> None:
        self._actions[key] = handler_id

    def register_actions(self, key: ModuleHandlerKey, handler_id: str) -> None:
        self._multi_actions[key] = handler_id

    def controller_id(self, key: HandlerKey) -> str | None:
        return self._controllers.get(key)

    def action_id(self, key: HandlerKey) -> str | None:
        return self._actions.get(key)

    def actions_id(self, key: ModuleHandlerKey) -> str | None:
        return self._multi_actions.get(key)

    def enable_plugin(self, app: str, plugin: str) -> None:
        self._plugins.add((app, plugin))

    def plugin_available(self, app: str, plugin: str) -> bool:
        return (app, plugin) in self._plugins
