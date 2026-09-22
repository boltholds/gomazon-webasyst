from datetime import timezone

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
    EventDispatchReport,
)
from gomazon_webasyst.application.events.vo.identity import EventName
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
)
from gomazon_webasyst.composition.team import create_team_runtime_module


class EmptyPublisher:
    async def publish(self, request):
        return EventDispatchReport(
            event=request.event,
            results=(),
            failures=(),
        )


def _app(app_id: str) -> InstalledApplication:
    return InstalledApplication(
        app_id=AppId(app_id),
        display_name=ApplicationDisplayName(app_id.title()),
        icons=ApplicationIconSet(()),
        vendor=ApplicationVendor("test"),
        version=ApplicationVersion("1.0"),
        capabilities=ApplicationCapabilities(frozenset()),
        header_items=ApplicationHeaderItems(()),
    )


async def test_team_runtime_registers_contacts_collection_relay() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    module = create_team_runtime_module(
        sessions,
        event_publisher=EmptyPublisher(),
        installed_applications=InMemoryInstalledApplicationCatalog(
            (_app("team"),)
        ),
        server_timezone=timezone.utc,
    )

    definitions = {
        definition.handler_id.value: definition
        for definition in module.event_handlers
    }

    assert set(definitions) >= {
        "team-contacts-delete-relay",
        "team-contacts-collection-relay",
    }
    collection = definitions["team-contacts-collection-relay"]
    assert collection.pattern.name == EventName("contacts_collection")

    await engine.dispose()
