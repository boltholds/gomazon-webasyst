from gomazon_webasyst.compatibility.webasyst.dispatch.registry import (
    InMemoryHandlerRegistry,
)
from gomazon_webasyst.contracts.dispatch import (
    ActionHandlerKey,
    AppNamespace,
    HandlerRegistered,
    ModuleHandlerKey,
    PluginNamespace,
)


def test_registry_stores_each_handler_kind_independently() -> None:
    registry = InMemoryHandlerRegistry()
    namespace = AppNamespace(app="blog")
    action_key = ActionHandlerKey(
        namespace=namespace,
        module="post",
        action="show",
    )
    module_key = ModuleHandlerKey(namespace=namespace, module="post")

    registry.register_controller(action_key, "controller")
    registry.register_action(action_key, "action")
    registry.register_actions(module_key, "actions")

    assert registry.controller_id(action_key) == HandlerRegistered(
        handler_id="controller"
    )
    assert registry.action_id(action_key) == HandlerRegistered(
        handler_id="action"
    )
    assert registry.actions_id(module_key) == HandlerRegistered(
        handler_id="actions"
    )


def test_keys_distinguish_app_and_plugin_namespaces() -> None:
    app_key = ModuleHandlerKey(
        namespace=AppNamespace(app="shop"),
        module="frontend",
    )
    plugin_key = ModuleHandlerKey(
        namespace=PluginNamespace(app="shop", plugin="reviews"),
        module="frontend",
    )

    assert app_key != plugin_key


def test_handler_registry_has_no_plugin_availability_state() -> None:
    registry = InMemoryHandlerRegistry()

    assert not hasattr(registry, "enable_plugin")
    assert not hasattr(registry, "plugin_available")
