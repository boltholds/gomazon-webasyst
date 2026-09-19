import pytest

pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

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
from gomazon_webasyst.composition.application_runtime import (
    InstalledKnownRuntimeModuleFactories,
    KnownRuntimeModuleFactory,
    ProvidedPluginCatalogSource,
    create_application_runtime_components,
)
from gomazon_webasyst.composition.team import create_team_runtime_module
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
)
from gomazon_webasyst.infrastructure.plugins.in_memory_catalog import (
    InMemoryInstalledPluginCatalog,
)


class RecordingNestedHandler:
    def __init__(self) -> None:
        self.calls = []

    async def handle(self, context, payload):
        self.calls.append((context, payload))
        return EventHandlerReturned(
            value=LegacyEventPayload(value={"nested": True})
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


@pytest.mark.asyncio
async def test_team_contacts_delete_relay_performs_nested_dispatch_without_outer_result() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    nested_handler = RecordingNestedHandler()

    def build_team(event_publisher):
        return create_team_runtime_module(
            sessions,
            event_publisher=event_publisher,
        )

    def build_audit(event_publisher):
        del event_publisher
        return ApplicationRuntimeModule(
            app_id=AppId("audit"),
            dispatch_handlers=(),
            api_methods=(),
            event_handlers=(
                EventHandlerDefinition(
                    handler_id=EventHandlerId("audit-team-contacts-delete"),
                    owner=ApplicationEventOwner(AppId("audit")),
                    source=ExactEventSource(AppId("team")),
                    pattern=ExactEventPattern(
                        EventName("contacts_delete")
                    ),
                    handler=nested_handler,
                ),
            ),
            plugins=(),
        )

    components = create_application_runtime_components(
        installed_applications=InMemoryInstalledApplicationCatalog(
            (_app("team"), _app("audit"))
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
                KnownRuntimeModuleFactory(
                    app_id=AppId("audit"),
                    build=build_audit,
                ),
            )
        ),
    )
    await components.bootstrap.initialize()

    payload = LegacyEventPayload(value={"id": [7, 8]})
    outer = await components.event_dispatcher.dispatch(
        EventDispatchRequest(
            event=EventKey(
                AppId("contacts"),
                EventName("delete"),
            ),
            payload=payload,
        )
    )

    assert outer.results == ()
    assert outer.failures == ()
    assert len(nested_handler.calls) == 1
    nested_context, nested_payload = nested_handler.calls[0]
    assert nested_context.event == EventKey(
        AppId("team"),
        EventName("contacts_delete"),
    )
    assert nested_payload is payload

    await engine.dispose()
