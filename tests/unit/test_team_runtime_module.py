import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

pytest.importorskip("aiosqlite")

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
from gomazon_webasyst.application.events.composites.dispatcher import EventDispatcher
from gomazon_webasyst.application.events.services.pattern_matcher import (
    EventPatternMatcher,
    EventPatternNotMatched,
)
from gomazon_webasyst.application.events.vo.identity import EventName
from gomazon_webasyst.application.events.vo.owners import ApplicationEventOwner
from gomazon_webasyst.application.events.vo.patterns import ExactEventSource
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.composition.team_directory import TeamRuntimeModuleFactory
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
)
from gomazon_webasyst.infrastructure.events.registry import (
    InMemoryEventHandlerRegistry,
)


class RejectRegex:
    def match(self, expression: str, event_name: EventName):
        return EventPatternNotMatched()


def _app(app_id: str) -> InstalledApplication:
    return InstalledApplication(
        app_id=AppId(app_id),
        display_name=ApplicationDisplayName(app_id.title()),
        icons=ApplicationIconSet(()),
        vendor=ApplicationVendor("webasyst"),
        version=ApplicationVersion("2.3.4"),
        capabilities=ApplicationCapabilities(frozenset()),
        header_items=ApplicationHeaderItems(()),
    )


def _dispatcher() -> EventDispatcher:
    return EventDispatcher(
        InMemoryEventHandlerRegistry(
            EventPatternMatcher(RejectRegex())
        )
    )


@pytest.mark.asyncio
async def test_team_runtime_factory_skips_absent_team_application() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        factory = TeamRuntimeModuleFactory(
            async_sessionmaker(engine, expire_on_commit=False),
            Settings(database_url="sqlite+aiosqlite:///:memory:"),
        )
        modules = await factory.build(
            InMemoryInstalledApplicationCatalog((_app("shop"),)),
            _dispatcher(),
        )
        assert modules == ()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_team_runtime_factory_declares_two_get_methods_and_contacts_bridge() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        factory = TeamRuntimeModuleFactory(
            async_sessionmaker(engine, expire_on_commit=False),
            Settings(database_url="sqlite+aiosqlite:///:memory:"),
        )
        modules = await factory.build(
            InMemoryInstalledApplicationCatalog((_app("team"),)),
            _dispatcher(),
        )
        assert len(modules) == 1
        module = modules[0]
        assert module.app_id == AppId("team")
        assert tuple(
            definition.target.method.value
            for definition in module.api_methods
        ) == ("users.getList", "groups.getList")
        assert all(
            {method.value for method in definition.allowed_methods}
            == {"GET"}
            for definition in module.api_methods
        )
        assert len(module.event_handlers) == 1
        event = module.event_handlers[0]
        assert event.owner == ApplicationEventOwner(AppId("team"))
        assert event.source == ExactEventSource(AppId("contacts"))
        assert event.pattern.name == EventName("contacts_collection")
    finally:
        await engine.dispose()
