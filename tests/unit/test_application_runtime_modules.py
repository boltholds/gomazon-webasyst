from dataclasses import FrozenInstanceError

import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_execution.entities.method_definition import (
    ApiMethodDefinition,
)
from gomazon_webasyst.application.api_execution.vo.method import (
    ApiHttpMethod,
    ApiMethodName,
    ApiMethodTarget,
)
from gomazon_webasyst.application.plugins.vo.identity import PluginId, PluginKey
from gomazon_webasyst.application.runtime.entities.application_module import (
    ApplicationRuntimeModule,
)
from gomazon_webasyst.application.runtime.entities.plugin_module import (
    PluginRuntimeModule,
)
from gomazon_webasyst.application.runtime.vo.dispatch import (
    ActionDispatchDefinition,
    DispatchHandlerId,
    PluginAvailabilityDefinition,
)
from gomazon_webasyst.contracts.dispatch import ActionHandlerKey, AppNamespace


class StubApiHandler:
    async def execute(self, context, parameters):
        raise AssertionError("not executed")


def _method(app_id: str, name: str = "ping") -> ApiMethodDefinition:
    return ApiMethodDefinition(
        target=ApiMethodTarget(AppId(app_id), ApiMethodName(name)),
        allowed_methods=frozenset({ApiHttpMethod("GET")}),
        handler=StubApiHandler(),
    )


def test_application_runtime_module_is_frozen_and_app_owned() -> None:
    module = ApplicationRuntimeModule(
        app_id=AppId("shop"),
        dispatch_handlers=(),
        api_methods=(_method("shop"),),
        event_handlers=(),
        plugins=(),
    )
    assert module.api_methods[0].target.app_id == AppId("shop")
    with pytest.raises(FrozenInstanceError):
        module.app_id = AppId("blog")  # type: ignore[misc]


def test_application_runtime_rejects_foreign_api_method() -> None:
    with pytest.raises(ValueError, match="another application"):
        ApplicationRuntimeModule(
            app_id=AppId("shop"),
            dispatch_handlers=(),
            api_methods=(_method("blog"),),
            event_handlers=(),
            plugins=(),
        )


def test_application_runtime_rejects_foreign_or_duplicate_plugin_modules() -> None:
    foreign = PluginRuntimeModule(
        key=PluginKey(AppId("blog"), PluginId("demo")),
        dispatch_handlers=(),
        api_methods=(),
        event_handlers=(),
    )
    with pytest.raises(ValueError, match="foreign"):
        ApplicationRuntimeModule(
            app_id=AppId("shop"),
            dispatch_handlers=(),
            api_methods=(),
            event_handlers=(),
            plugins=(foreign,),
        )

    plugin = PluginRuntimeModule(
        key=PluginKey(AppId("shop"), PluginId("demo")),
        dispatch_handlers=(),
        api_methods=(),
        event_handlers=(),
    )
    with pytest.raises(ValueError, match="duplicate"):
        ApplicationRuntimeModule(
            app_id=AppId("shop"),
            dispatch_handlers=(),
            api_methods=(),
            event_handlers=(),
            plugins=(plugin, plugin),
        )


def test_plugin_runtime_api_contribution_must_belong_to_parent_application() -> None:
    with pytest.raises(ValueError, match="another application"):
        PluginRuntimeModule(
            key=PluginKey(AppId("shop"), PluginId("demo")),
            dispatch_handlers=(),
            api_methods=(_method("blog"),),
            event_handlers=(),
        )


def test_dispatch_definitions_are_typed_and_do_not_embed_import_paths() -> None:
    action = ActionDispatchDefinition(
        key=ActionHandlerKey(
            namespace=AppNamespace(app="shop"),
            module="backend",
            action="index",
        ),
        handler_id=DispatchHandlerId("shop-backend-index"),
    )
    plugin = PluginAvailabilityDefinition(
        PluginKey(AppId("shop"), PluginId("demo"))
    )
    assert action.handler_id.value == "shop-backend-index"
    assert plugin.key.plugin_id == PluginId("demo")


def test_dispatch_handler_id_rejects_empty() -> None:
    with pytest.raises(ValueError):
        DispatchHandlerId("")
