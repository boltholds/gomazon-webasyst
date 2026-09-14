from gomazon_webasyst.compatibility.webasyst.dispatch.registry import InMemoryDispatchRegistry
from gomazon_webasyst.contracts.dispatch import (
    ActionHandlerKey,
    AppNamespace,
    ModuleHandlerKey,
    PluginNamespace,
)


def test_registry_stores_each_handler_kind_independently() -> None:
    registry = InMemoryDispatchRegistry()
    namespace = AppNamespace(app="blog")
    action_key = ActionHandlerKey(namespace=namespace, module="post", action="show")
    module_key = ModuleHandlerKey(namespace=namespace, module="post")

    registry.register_controller(action_key, "controller")
    registry.register_action(action_key, "action")
    registry.register_actions(module_key, "actions")

    assert registry.controller_id(action_key) == "controller"
    assert registry.action_id(action_key) == "action"
    assert registry.actions_id(module_key) == "actions"


def test_plugin_availability_is_explicit() -> None:
    registry = InMemoryDispatchRegistry()
    assert registry.plugin_available("shop", "reviews") is False
    registry.enable_plugin("shop", "reviews")
    assert registry.plugin_available("shop", "reviews") is True


def test_keys_distinguish_app_and_plugin_namespaces() -> None:
    app_key = ModuleHandlerKey(namespace=AppNamespace(app="shop"), module="frontend")
    plugin_key = ModuleHandlerKey(
        namespace=PluginNamespace(app="shop", plugin="reviews"), module="frontend"
    )
    assert app_key != plugin_key
