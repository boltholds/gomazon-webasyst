import pytest

from gomazon_webasyst.compatibility.webasyst.dispatch.errors import (
    DispatchTargetNotFound,
    PluginUnavailable,
)
from gomazon_webasyst.compatibility.webasyst.dispatch.registry import InMemoryDispatchRegistry
from gomazon_webasyst.compatibility.webasyst.dispatch.resolver import DispatchResolver
from gomazon_webasyst.contracts.dispatch import (
    ActionDispatch,
    ActionHandlerKey,
    AppNamespace,
    ControllerTarget,
    DefaultDispatch,
    ModuleHandlerKey,
    MultiActionTarget,
    PluginNamespace,
    SingleActionTarget,
)


def explicit_request():
    return ActionDispatch(
        namespace=AppNamespace(app="blog"), module="post", action="show"
    )


def test_controller_wins_over_single_action_and_multi_actions() -> None:
    registry = InMemoryDispatchRegistry()
    action_key = ActionHandlerKey(
        namespace=AppNamespace(app="blog"), module="post", action="show"
    )
    module_key = ModuleHandlerKey(namespace=AppNamespace(app="blog"), module="post")
    registry.register_controller(action_key, "controller")
    registry.register_action(action_key, "action")
    registry.register_actions(module_key, "actions")
    assert DispatchResolver(registry).resolve(explicit_request()) == ControllerTarget(
        handler_id="controller"
    )


def test_single_action_wins_when_controller_missing() -> None:
    registry = InMemoryDispatchRegistry()
    action_key = ActionHandlerKey(
        namespace=AppNamespace(app="blog"), module="post", action="show"
    )
    module_key = ModuleHandlerKey(namespace=AppNamespace(app="blog"), module="post")
    registry.register_action(action_key, "action")
    registry.register_actions(module_key, "actions")
    assert DispatchResolver(registry).resolve(explicit_request()) == SingleActionTarget(
        handler_id="action"
    )


def test_multi_actions_receives_explicit_action_method() -> None:
    registry = InMemoryDispatchRegistry()
    module_key = ModuleHandlerKey(namespace=AppNamespace(app="blog"), module="post")
    registry.register_actions(module_key, "actions")
    assert DispatchResolver(registry).resolve(explicit_request()) == MultiActionTarget(
        handler_id="actions", action_method="show"
    )


def test_default_multi_actions_target_uses_default_action() -> None:
    registry = InMemoryDispatchRegistry()
    request = DefaultDispatch(namespace=AppNamespace(app="blog"), module="frontend")
    module_key = ModuleHandlerKey(namespace=request.namespace, module="frontend")
    registry.register_actions(module_key, "frontend-actions")
    assert DispatchResolver(registry).resolve(request) == MultiActionTarget(
        handler_id="frontend-actions", action_method="default"
    )


def test_try_default_retries_same_namespace_and_module_without_action() -> None:
    registry = InMemoryDispatchRegistry()
    module_key = ModuleHandlerKey(namespace=AppNamespace(app="blog"), module="post")
    registry.register_controller(module_key, "default-controller")
    assert DispatchResolver(registry).resolve(
        explicit_request(), try_default=True
    ) == ControllerTarget(handler_id="default-controller")


def test_missing_target_raises_typed_404_error() -> None:
    with pytest.raises(DispatchTargetNotFound):
        DispatchResolver(InMemoryDispatchRegistry()).resolve(explicit_request())


def test_disabled_plugin_fails_before_handler_resolution() -> None:
    request = ActionDispatch(
        namespace=PluginNamespace(app="shop", plugin="reviews"),
        module="frontend",
        action="list",
    )
    with pytest.raises(PluginUnavailable):
        DispatchResolver(InMemoryDispatchRegistry()).resolve(request)
