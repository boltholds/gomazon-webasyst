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
from gomazon_webasyst.application.application_registry.entities.installed_application import (
    InstalledApplication,
)
from gomazon_webasyst.application.application_registry.vo.capabilities import (
    ApplicationCapabilities,
)
from gomazon_webasyst.application.application_registry.vo.header_items import (
    ApplicationHeaderItems,
)
from gomazon_webasyst.application.application_registry.vo.icons import (
    ApplicationIconSet,
)
from gomazon_webasyst.application.application_registry.vo.metadata import (
    ApplicationDisplayName,
    ApplicationVendor,
    ApplicationVersion,
)
from gomazon_webasyst.application.runtime.entities.application_module import (
    ApplicationRuntimeModule,
)
from gomazon_webasyst.composition.application_runtime import (
    ApplicationRuntimePending,
    ApplicationRuntimeReady,
)
from gomazon_webasyst.composition.container import (
    create_container_with_runtime_catalogs,
)
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.infrastructure.api_execution.method_registry import (
    InMemoryApiMethodRegistry,
)
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
)
from gomazon_webasyst.infrastructure.plugins.in_memory_catalog import (
    InMemoryInstalledPluginCatalog,
)


class StubApiHandler:
    async def execute(self, context, parameters):
        raise AssertionError("not executed")


def _app(app_id: str) -> InstalledApplication:
    return InstalledApplication(
        app_id=AppId(app_id),
        display_name=ApplicationDisplayName(app_id.title()),
        icons=ApplicationIconSet(()),
        vendor=ApplicationVendor("example"),
        version=ApplicationVersion("1.0.0"),
        capabilities=ApplicationCapabilities(frozenset()),
        header_items=ApplicationHeaderItems(()),
    )


def _api(app_id: str) -> ApiMethodDefinition:
    return ApiMethodDefinition(
        target=ApiMethodTarget(AppId(app_id), ApiMethodName("ping")),
        allowed_methods=frozenset({ApiHttpMethod("GET")}),
        handler=StubApiHandler(),
    )


@pytest.mark.asyncio
async def test_container_runtime_initializes_before_use_and_shares_api_registry() -> None:
    apps = InMemoryInstalledApplicationCatalog((_app("shop"),))
    plugins = InMemoryInstalledPluginCatalog(())
    method = _api("shop")
    module = ApplicationRuntimeModule(
        app_id=AppId("shop"),
        dispatch_handlers=(),
        api_methods=(method,),
        event_handlers=(),
        plugins=(),
    )
    container = create_container_with_runtime_catalogs(
        Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            webasyst_root="/definitely/not/used",
        ),
        installed_application_catalog=apps,
        installed_plugin_catalog=plugins,
        runtime_modules=(module,),
    )
    try:
        assert isinstance(
            container.application_runtime.bootstrap.state,
            ApplicationRuntimePending,
        )
        assert (
            container.api_execution.method_registry
            is container.application_runtime.api_method_registry
        )

        await container.initialize()

        assert isinstance(
            container.application_runtime.bootstrap.state,
            ApplicationRuntimeReady,
        )
        resolved = container.api_execution.method_registry.resolve(method.target)
        assert resolved.definition is method
    finally:
        await container.close()


@pytest.mark.asyncio
async def test_installed_app_without_runtime_module_remains_non_executable() -> None:
    apps = InMemoryInstalledApplicationCatalog((_app("shop"),))
    container = create_container_with_runtime_catalogs(
        Settings(database_url="sqlite+aiosqlite:///:memory:"),
        installed_application_catalog=apps,
        installed_plugin_catalog=InMemoryInstalledPluginCatalog(()),
        runtime_modules=(),
    )
    try:
        await container.initialize()
        target = ApiMethodTarget(AppId("shop"), ApiMethodName("ping"))
        assert type(
            container.application_runtime.api_method_registry.resolve(target)
        ).__name__ == "ApiMethodMissing"
        assert isinstance(
            container.application_runtime.api_method_registry,
            InMemoryApiMethodRegistry,
        )
    finally:
        await container.close()


@pytest.mark.asyncio
async def test_runtime_initialize_is_idempotent() -> None:
    container = create_container_with_runtime_catalogs(
        Settings(database_url="sqlite+aiosqlite:///:memory:"),
        installed_application_catalog=InMemoryInstalledApplicationCatalog(
            (_app("shop"),)
        ),
        installed_plugin_catalog=InMemoryInstalledPluginCatalog(()),
        runtime_modules=(),
    )
    try:
        first = await container.application_runtime.bootstrap.initialize()
        second = await container.application_runtime.bootstrap.initialize()
        assert first is second
    finally:
        await container.close()
