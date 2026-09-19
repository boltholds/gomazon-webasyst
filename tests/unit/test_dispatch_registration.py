from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.plugins.vo.identity import PluginId, PluginKey
from gomazon_webasyst.application.ports.dispatch_registration import (
    DispatchRegistered,
    DispatchRegistrationAvailable,
    DispatchRegistrationConflict,
    DispatchRegistrationRejected,
)
from gomazon_webasyst.application.runtime.vo.dispatch import (
    ActionDispatchDefinition,
    ControllerDispatchDefinition,
    DispatchHandlerId,
    MultiActionDispatchDefinition,
    PluginAvailabilityDefinition,
)
from gomazon_webasyst.compatibility.webasyst.dispatch.registry import (
    InMemoryDispatchRegistry,
)
from gomazon_webasyst.contracts.dispatch import (
    ActionHandlerKey,
    AppNamespace,
    HandlerMissing,
    HandlerRegistered,
    ModuleHandlerKey,
    PluginAvailable,
)


def test_typed_dispatch_registration_checks_without_mutating() -> None:
    registry = InMemoryDispatchRegistry()
    key = ActionHandlerKey(
        namespace=AppNamespace(app="shop"),
        module="backend",
        action="index",
    )
    definition = ActionDispatchDefinition(
        key=key,
        handler_id=DispatchHandlerId("shop-index"),
    )

    assert isinstance(registry.check(definition), DispatchRegistrationAvailable)
    assert isinstance(registry.action_id(key), HandlerMissing)
    assert isinstance(registry.register(definition), DispatchRegistered)
    assert registry.action_id(key) == HandlerRegistered(handler_id="shop-index")
    assert isinstance(registry.check(definition), DispatchRegistrationConflict)
    assert isinstance(registry.register(definition), DispatchRegistrationRejected)
    assert registry.action_id(key) == HandlerRegistered(handler_id="shop-index")


def test_handler_kinds_have_independent_collision_domains() -> None:
    registry = InMemoryDispatchRegistry()
    action_key = ActionHandlerKey(
        namespace=AppNamespace(app="shop"),
        module="backend",
        action="index",
    )
    module_key = ModuleHandlerKey(
        namespace=AppNamespace(app="shop"),
        module="backend",
    )
    controller = ControllerDispatchDefinition(
        key=action_key,
        handler_id=DispatchHandlerId("controller"),
    )
    action = ActionDispatchDefinition(
        key=action_key,
        handler_id=DispatchHandlerId("action"),
    )
    multi = MultiActionDispatchDefinition(
        key=module_key,
        handler_id=DispatchHandlerId("multi"),
    )

    assert isinstance(registry.register(controller), DispatchRegistered)
    assert isinstance(registry.register(action), DispatchRegistered)
    assert isinstance(registry.register(multi), DispatchRegistered)
    assert registry.controller_id(action_key) == HandlerRegistered(
        handler_id="controller"
    )
    assert registry.action_id(action_key) == HandlerRegistered(
        handler_id="action"
    )
    assert registry.actions_id(module_key) == HandlerRegistered(
        handler_id="multi"
    )


def test_plugin_availability_registration_is_explicit_and_duplicate_safe() -> None:
    registry = InMemoryDispatchRegistry()
    definition = PluginAvailabilityDefinition(
        PluginKey(AppId("shop"), PluginId("reviews"))
    )
    assert isinstance(registry.register(definition), DispatchRegistered)
    assert isinstance(
        registry.plugin_available("shop", "reviews"),
        PluginAvailable,
    )
    assert isinstance(registry.register(definition), DispatchRegistrationRejected)


def test_legacy_convenience_registration_methods_use_typed_duplicate_rules() -> None:
    registry = InMemoryDispatchRegistry()
    key = ActionHandlerKey(
        namespace=AppNamespace(app="blog"),
        module="post",
        action="show",
    )

    first = registry.register_action(key, "first")
    duplicate = registry.register_action(key, "second")

    assert isinstance(first, DispatchRegistered)
    assert isinstance(duplicate, DispatchRegistrationRejected)
    assert registry.action_id(key) == HandlerRegistered(handler_id="first")
