import pytest

from gomazon_webasyst.application.app_values import AppId, PluginId, PluginRef
from gomazon_webasyst.application.application_registry import (
    ApplicationCatalog,
    InstallationManifest,
    InstalledApplication,
    StaticApplicationRegistry,
)
from gomazon_webasyst.compatibility.webasyst.dispatch.errors import (
    ApplicationUnavailable,
    DispatchTargetNotFound,
    PluginUnavailable,
)
from gomazon_webasyst.compatibility.webasyst.dispatch.registry import (
    InMemoryHandlerRegistry,
)
from gomazon_webasyst.compatibility.webasyst.dispatch.resolver import (
    DispatchResolver,
)
from gomazon_webasyst.contracts.applications import (
    ApplicationDescriptor,
    PluginDescriptor,
)
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


def _applications(
    *,
    reviews_enabled: bool = False,
) -> StaticApplicationRegistry:
    catalog = ApplicationCatalog(
        applications=(
            ApplicationDescriptor(id=AppId("blog"), name="Blog"),
            ApplicationDescriptor(id=AppId("shop"), name="Shop"),
            ApplicationDescriptor(id=AppId("photos"), name="Photos"),
        ),
        plugins=(
            PluginDescriptor(
                ref=PluginRef(AppId("shop"), PluginId("reviews")),
                name="Reviews",
            ),
        ),
    )
    shop_plugins = (
        (PluginId("reviews"),)
        if reviews_enabled
        else ()
    )
    manifest = InstallationManifest(
        apps=(
            InstalledApplication(AppId("blog")),
            InstalledApplication(AppId("shop"), shop_plugins),
        )
    )
    return StaticApplicationRegistry(catalog, manifest)


def _resolver(
    handlers: InMemoryHandlerRegistry,
    *,
    reviews_enabled: bool = False,
) -> DispatchResolver:
    return DispatchResolver(
        handlers,
        _applications(reviews_enabled=reviews_enabled),
    )


def explicit_request() -> ActionDispatch:
    return ActionDispatch(
        namespace=AppNamespace(app="blog"),
        module="post",
        action="show",
    )


def test_controller_wins_over_single_action_and_multi_actions() -> None:
    handlers = InMemoryHandlerRegistry()
    action_key = ActionHandlerKey(
        namespace=AppNamespace(app="blog"),
        module="post",
        action="show",
    )
    module_key = ModuleHandlerKey(
        namespace=AppNamespace(app="blog"),
        module="post",
    )
    handlers.register_controller(action_key, "controller")
    handlers.register_action(action_key, "action")
    handlers.register_actions(module_key, "actions")

    assert _resolver(handlers).resolve(explicit_request()) == ControllerTarget(
        handler_id="controller"
    )


def test_single_action_wins_when_controller_missing() -> None:
    handlers = InMemoryHandlerRegistry()
    action_key = ActionHandlerKey(
        namespace=AppNamespace(app="blog"),
        module="post",
        action="show",
    )
    module_key = ModuleHandlerKey(
        namespace=AppNamespace(app="blog"),
        module="post",
    )
    handlers.register_action(action_key, "action")
    handlers.register_actions(module_key, "actions")

    assert _resolver(handlers).resolve(explicit_request()) == SingleActionTarget(
        handler_id="action"
    )


def test_multi_actions_receives_explicit_action_method() -> None:
    handlers = InMemoryHandlerRegistry()
    module_key = ModuleHandlerKey(
        namespace=AppNamespace(app="blog"),
        module="post",
    )
    handlers.register_actions(module_key, "actions")

    assert _resolver(handlers).resolve(explicit_request()) == MultiActionTarget(
        handler_id="actions",
        action_method="show",
    )


def test_default_multi_actions_target_uses_default_action() -> None:
    handlers = InMemoryHandlerRegistry()
    request = DefaultDispatch(
        namespace=AppNamespace(app="blog"),
        module="frontend",
    )
    module_key = ModuleHandlerKey(
        namespace=request.namespace,
        module="frontend",
    )
    handlers.register_actions(module_key, "frontend-actions")

    assert _resolver(handlers).resolve(request) == MultiActionTarget(
        handler_id="frontend-actions",
        action_method="default",
    )


def test_try_default_retries_same_namespace_and_module_without_action() -> None:
    handlers = InMemoryHandlerRegistry()
    module_key = ModuleHandlerKey(
        namespace=AppNamespace(app="blog"),
        module="post",
    )
    handlers.register_controller(module_key, "default-controller")

    assert _resolver(handlers).resolve(
        explicit_request(),
        try_default=True,
    ) == ControllerTarget(handler_id="default-controller")


def test_enabled_app_with_missing_target_raises_typed_404_error() -> None:
    with pytest.raises(DispatchTargetNotFound):
        _resolver(InMemoryHandlerRegistry()).resolve(explicit_request())


def test_disabled_application_fails_before_handler_resolution() -> None:
    request = DefaultDispatch(
        namespace=AppNamespace(app="photos"),
        module="frontend",
    )

    with pytest.raises(ApplicationUnavailable):
        _resolver(InMemoryHandlerRegistry()).resolve(request)


def test_disabled_plugin_fails_before_handler_resolution() -> None:
    request = ActionDispatch(
        namespace=PluginNamespace(app="shop", plugin="reviews"),
        module="frontend",
        action="list",
    )

    with pytest.raises(PluginUnavailable):
        _resolver(InMemoryHandlerRegistry()).resolve(request)


def test_enabled_plugin_without_handler_is_target_not_found() -> None:
    request = ActionDispatch(
        namespace=PluginNamespace(app="shop", plugin="reviews"),
        module="frontend",
        action="list",
    )

    with pytest.raises(DispatchTargetNotFound):
        _resolver(
            InMemoryHandlerRegistry(),
            reviews_enabled=True,
        ).resolve(request)


def test_enabled_plugin_with_registered_handler_resolves() -> None:
    handlers = InMemoryHandlerRegistry()
    request = ActionDispatch(
        namespace=PluginNamespace(app="shop", plugin="reviews"),
        module="frontend",
        action="list",
    )
    key = ActionHandlerKey(
        namespace=request.namespace,
        module="frontend",
        action="list",
    )
    handlers.register_action(key, "reviews-list")

    assert _resolver(
        handlers,
        reviews_enabled=True,
    ).resolve(request) == SingleActionTarget(handler_id="reviews-list")
