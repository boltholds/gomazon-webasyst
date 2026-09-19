import pytest

from gomazon_webasyst.application.access_values import AppId
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
    InstalledKnownRuntimeModuleFactories,
    KnownRuntimeModuleFactory,
    ProvidedPluginCatalogSource,
    RuntimeModuleFactoryMismatch,
    create_application_runtime_components,
)
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
)
from gomazon_webasyst.infrastructure.plugins.in_memory_catalog import (
    InMemoryInstalledPluginCatalog,
)


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


def _empty_module(app_id: str) -> ApplicationRuntimeModule:
    return ApplicationRuntimeModule(
        app_id=AppId(app_id),
        dispatch_handlers=(),
        api_methods=(),
        event_handlers=(),
        plugins=(),
    )


@pytest.mark.asyncio
async def test_known_factory_is_not_called_when_application_is_not_installed() -> None:
    calls: list[str] = []

    def build_team(event_publisher):
        del event_publisher
        calls.append("team")
        return _empty_module("team")

    components = create_application_runtime_components(
        installed_applications=InMemoryInstalledApplicationCatalog(
            (_app("shop"),)
        ),
        plugin_source=ProvidedPluginCatalogSource(
            InMemoryInstalledPluginCatalog(())
        ),
        module_source=InstalledKnownRuntimeModuleFactories(
            (
                KnownRuntimeModuleFactory(
                    app_id=AppId("team"),
                    build=build_team,
                ),
            )
        ),
    )

    ready = await components.bootstrap.initialize()

    assert calls == []
    assert ready.linked.applications == ()


@pytest.mark.asyncio
async def test_known_factory_identity_mismatch_fails_before_linking() -> None:
    def build_wrong(event_publisher):
        del event_publisher
        return _empty_module("shop")

    components = create_application_runtime_components(
        installed_applications=InMemoryInstalledApplicationCatalog(
            (_app("team"),)
        ),
        plugin_source=ProvidedPluginCatalogSource(
            InMemoryInstalledPluginCatalog(())
        ),
        module_source=InstalledKnownRuntimeModuleFactories(
            (
                KnownRuntimeModuleFactory(
                    app_id=AppId("team"),
                    build=build_wrong,
                ),
            )
        ),
    )

    with pytest.raises(RuntimeModuleFactoryMismatch, match="declared=team"):
        await components.bootstrap.initialize()
