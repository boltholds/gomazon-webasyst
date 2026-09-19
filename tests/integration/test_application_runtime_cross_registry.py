from pathlib import Path

import pytest

pytest.importorskip("aiosqlite")

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_execution.entities.method_definition import (
    ApiMethodDefinition,
)
from gomazon_webasyst.application.api_execution.vo.method import (
    ApiHttpMethod,
    ApiMethodName,
    ApiMethodTarget,
)
from gomazon_webasyst.application.events.composites.contracts import (
    EventDispatchRequest,
)
from gomazon_webasyst.application.events.entities.handler_definition import (
    EventHandlerDefinition,
)
from gomazon_webasyst.application.events.vo.identity import (
    EventHandlerId,
    EventKey,
    EventName,
)
from gomazon_webasyst.application.events.vo.owners import ApplicationEventOwner
from gomazon_webasyst.application.events.vo.patterns import (
    ExactEventPattern,
    ExactEventSource,
)
from gomazon_webasyst.application.events.vo.payload import (
    EventHandlerReturned,
    LegacyEventPayload,
)
from gomazon_webasyst.application.runtime.entities.application_module import (
    ApplicationRuntimeModule,
)
from gomazon_webasyst.application.runtime.vo.dispatch import (
    ActionDispatchDefinition,
    DispatchHandlerId,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.installer_policy import (
    NeverForceInstaller,
)
from gomazon_webasyst.composition.container import (
    create_container_with_runtime_catalogs,
)
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.contracts.dispatch import (
    ActionHandlerKey,
    AppNamespace,
    HandlerMissing,
    HandlerRegistered,
)
from gomazon_webasyst.infrastructure.application_registry.filesystem_catalog import (
    FilesystemInstalledApplicationCatalog,
)
from gomazon_webasyst.infrastructure.plugins.filesystem_catalog import (
    FilesystemInstalledPluginCatalog,
)


class ApiHandler:
    async def execute(self, context, parameters):
        raise AssertionError("API execution is not needed for registry proof")


class RuntimeEventHandler:
    async def handle(self, context, payload):
        return EventHandlerReturned(
            value=LegacyEventPayload(
                value={
                    "handler": context.handler_id.value,
                    "payload": payload.model_dump(mode="json"),
                }
            )
        )


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "webasyst"
    root.mkdir()
    _write(
        root,
        "wa-config/apps.php",
        "<?php return ['shop' => true];",
    )
    _write(
        root,
        "wa-apps/shop/lib/config/app.php",
        "<?php return ['name' => 'Shop', 'vendor' => 'example', "
        "'version' => '1.0.0'];",
    )
    _write(
        root,
        "wa-system/webasyst/lib/config/app.php",
        "<?php return ['name' => 'Webasyst', 'vendor' => 'webasyst', "
        "'version' => '4.2.0'];",
    )
    return root


def _module() -> tuple[
    ApplicationRuntimeModule,
    ApiMethodDefinition,
    ActionHandlerKey,
]:
    method = ApiMethodDefinition(
        target=ApiMethodTarget(AppId("shop"), ApiMethodName("runtime.ping")),
        allowed_methods=frozenset({ApiHttpMethod("GET")}),
        handler=ApiHandler(),
    )
    dispatch_key = ActionHandlerKey(
        namespace=AppNamespace(app="shop"),
        module="backend",
        action="runtime",
    )
    event = EventHandlerDefinition(
        handler_id=EventHandlerId("shop-runtime-event"),
        owner=ApplicationEventOwner(AppId("shop")),
        source=ExactEventSource(AppId("shop")),
        pattern=ExactEventPattern(EventName("runtime.ready")),
        handler=RuntimeEventHandler(),
    )
    module = ApplicationRuntimeModule(
        app_id=AppId("shop"),
        dispatch_handlers=(
            ActionDispatchDefinition(
                key=dispatch_key,
                handler_id=DispatchHandlerId("shop-runtime-dispatch"),
            ),
        ),
        api_methods=(method,),
        event_handlers=(event,),
        plugins=(),
    )
    return module, method, dispatch_key


@pytest.mark.asyncio
async def test_one_explicit_runtime_module_links_api_dispatch_and_event(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    apps = FilesystemInstalledApplicationCatalog(
        root,
        installer_policy=NeverForceInstaller(),
    )
    plugins = FilesystemInstalledPluginCatalog(
        root,
        await apps.snapshot(),
    )
    module, method, dispatch_key = _module()

    container = create_container_with_runtime_catalogs(
        Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            webasyst_root=root,
        ),
        installed_application_catalog=apps,
        installed_plugin_catalog=plugins,
        runtime_modules=(module,),
    )
    try:
        await container.initialize()

        resolved_api = container.application_runtime.api_method_registry.resolve(
            method.target
        )
        assert resolved_api.definition is method
        assert container.application_runtime.dispatch_registry.action_id(
            dispatch_key
        ) == HandlerRegistered(handler_id="shop-runtime-dispatch")

        report = await container.application_runtime.event_dispatcher.dispatch(
            EventDispatchRequest(
                event=EventKey(
                    AppId("shop"),
                    EventName("runtime.ready"),
                ),
                payload=LegacyEventPayload(value={"source": "integration"}),
            )
        )
        assert len(report.results) == 1
        assert report.results[0].handler_id == EventHandlerId(
            "shop-runtime-event"
        )
        assert report.results[0].value.value["handler"] == (
            "shop-runtime-event"
        )
    finally:
        await container.close()


@pytest.mark.asyncio
async def test_installed_app_without_runtime_module_has_no_executable_capabilities(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    apps = FilesystemInstalledApplicationCatalog(
        root,
        installer_policy=NeverForceInstaller(),
    )
    plugins = FilesystemInstalledPluginCatalog(
        root,
        await apps.snapshot(),
    )
    _, method, dispatch_key = _module()

    container = create_container_with_runtime_catalogs(
        Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            webasyst_root=root,
        ),
        installed_application_catalog=apps,
        installed_plugin_catalog=plugins,
        runtime_modules=(),
    )
    try:
        await container.initialize()

        assert type(
            container.application_runtime.api_method_registry.resolve(
                method.target
            )
        ).__name__ == "ApiMethodMissing"
        assert isinstance(
            container.application_runtime.dispatch_registry.action_id(
                dispatch_key
            ),
            HandlerMissing,
        )
        report = await container.application_runtime.event_dispatcher.dispatch(
            EventDispatchRequest(
                event=EventKey(
                    AppId("shop"),
                    EventName("runtime.ready"),
                ),
                payload=LegacyEventPayload(value={}),
            )
        )
        assert report.results == ()
        assert report.failures == ()
    finally:
        await container.close()
