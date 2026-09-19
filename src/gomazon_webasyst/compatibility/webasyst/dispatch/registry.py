from gomazon_webasyst.application.ports.dispatch_registration import (
    DispatchRegistered,
    DispatchRegistrationAvailable,
    DispatchRegistrationCheck,
    DispatchRegistrationConflict,
    DispatchRegistrationRejected,
    DispatchRegistrationResult,
)
from gomazon_webasyst.application.runtime.vo.dispatch import (
    ActionDispatchDefinition,
    ControllerDispatchDefinition,
    DispatchHandlerId,
    DispatchRuntimeDefinition,
    MultiActionDispatchDefinition,
    PluginAvailabilityDefinition,
)
from gomazon_webasyst.contracts.dispatch import (
    HandlerKey,
    HandlerMissing,
    HandlerRegistered,
    HandlerRegistryLookup,
    ModuleHandlerKey,
    PluginAvailable,
    PluginMissing,
    PluginRegistryLookup,
)


class InMemoryDispatchRegistry:
    def __init__(self) -> None:
        self._controllers: dict[HandlerKey, str] = {}
        self._actions: dict[HandlerKey, str] = {}
        self._multi_actions: dict[ModuleHandlerKey, str] = {}
        self._plugins: set[tuple[str, str]] = set()

    def check(
        self,
        definition: DispatchRuntimeDefinition,
    ) -> DispatchRegistrationCheck:
        if isinstance(definition, ControllerDispatchDefinition):
            exists = definition.key in self._controllers
        elif isinstance(definition, ActionDispatchDefinition):
            exists = definition.key in self._actions
        elif isinstance(definition, MultiActionDispatchDefinition):
            exists = definition.key in self._multi_actions
        elif isinstance(definition, PluginAvailabilityDefinition):
            exists = (
                definition.key.app_id.value,
                definition.key.plugin_id.value,
            ) in self._plugins
        else:
            raise AssertionError("unsupported dispatch runtime definition")
        if exists:
            return DispatchRegistrationConflict(definition)
        return DispatchRegistrationAvailable(definition)

    def register(
        self,
        definition: DispatchRuntimeDefinition,
    ) -> DispatchRegistrationResult:
        if isinstance(self.check(definition), DispatchRegistrationConflict):
            return DispatchRegistrationRejected(definition)

        if isinstance(definition, ControllerDispatchDefinition):
            self._controllers[definition.key] = definition.handler_id.value
        elif isinstance(definition, ActionDispatchDefinition):
            self._actions[definition.key] = definition.handler_id.value
        elif isinstance(definition, MultiActionDispatchDefinition):
            self._multi_actions[definition.key] = definition.handler_id.value
        elif isinstance(definition, PluginAvailabilityDefinition):
            self._plugins.add(
                (
                    definition.key.app_id.value,
                    definition.key.plugin_id.value,
                )
            )
        else:
            raise AssertionError("unsupported dispatch runtime definition")
        return DispatchRegistered(definition)

    def register_controller(
        self,
        key: HandlerKey,
        handler_id: str,
    ) -> DispatchRegistrationResult:
        return self.register(
            ControllerDispatchDefinition(
                key=key,
                handler_id=DispatchHandlerId(handler_id),
            )
        )

    def register_action(
        self,
        key: HandlerKey,
        handler_id: str,
    ) -> DispatchRegistrationResult:
        return self.register(
            ActionDispatchDefinition(
                key=key,
                handler_id=DispatchHandlerId(handler_id),
            )
        )

    def register_actions(
        self,
        key: ModuleHandlerKey,
        handler_id: str,
    ) -> DispatchRegistrationResult:
        return self.register(
            MultiActionDispatchDefinition(
                key=key,
                handler_id=DispatchHandlerId(handler_id),
            )
        )

    def enable_plugin(
        self,
        app: str,
        plugin: str,
    ) -> DispatchRegistrationResult:
        from gomazon_webasyst.application.access_values import AppId
        from gomazon_webasyst.application.plugins.vo.identity import PluginId, PluginKey

        return self.register(
            PluginAvailabilityDefinition(
                PluginKey(AppId(app), PluginId(plugin))
            )
        )

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

    def plugin_available(self, app: str, plugin: str) -> PluginRegistryLookup:
        if (app, plugin) in self._plugins:
            return PluginAvailable()
        return PluginMissing()
