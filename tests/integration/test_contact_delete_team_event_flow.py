from datetime import datetime

import pytest
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
from gomazon_webasyst.application.contact_deletion import ContactDeletionBatch
from gomazon_webasyst.application.contacts import DeleteContacts
from gomazon_webasyst.application.events.entities.handler_definition import (
    EventHandlerDefinition,
)
from gomazon_webasyst.application.events.vo.contacts import (
    ContactsDeleteEventPayload,
)
from gomazon_webasyst.application.events.vo.identity import EventHandlerId, EventName
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
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import WaContactRow
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.unit_of_work import (
    SQLAlchemyUnitOfWorkFactory,
)
from gomazon_webasyst.infrastructure.plugins.in_memory_catalog import (
    InMemoryInstalledPluginCatalog,
)


_AUXILIARY_DDL = (
    "CREATE TABLE wa_verification_channel_assets (id INTEGER PRIMARY KEY, address TEXT NOT NULL)",
    "CREATE TABLE wa_contact_settings (contact_id INTEGER NOT NULL, app_id TEXT, name TEXT, value TEXT)",
    "CREATE TABLE wa_app_tokens (token TEXT PRIMARY KEY, contact_id INTEGER NOT NULL)",
    "CREATE TABLE wa_contact_data_text (id INTEGER PRIMARY KEY, contact_id INTEGER NOT NULL, value TEXT)",
    "CREATE TABLE wa_contact_categories (contact_id INTEGER NOT NULL, category_id INTEGER NOT NULL)",
    "CREATE TABLE wa_contact_category (id INTEGER PRIMARY KEY, cnt INTEGER NOT NULL)",
    "CREATE TABLE wa_contact_events (id INTEGER PRIMARY KEY, contact_id INTEGER NOT NULL)",
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


class InspectingTeamDeleteConsumer:
    def __init__(self, sessions) -> None:
        self._sessions = sessions
        self.seen_payloads = []
        self.contact_existed_during_event = False

    async def handle(self, context, payload):
        assert isinstance(payload, ContactsDeleteEventPayload)
        self.seen_payloads.append(payload)
        async with self._sessions() as session:
            self.contact_existed_during_event = (
                await session.get(WaContactRow, payload.contact_ids[0])
            ) is not None
        return EventHandlerReturned(
            value=LegacyEventPayload(value={"observed": True})
        )


@pytest.mark.asyncio
async def test_real_contact_delete_triggers_team_relay_before_sql_cleanup() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        for ddl in _AUXILIARY_DDL:
            await connection.exec_driver_sql(ddl)

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add(
            WaContactRow(
                id=1,
                name="Delete Me",
                firstname="Delete",
                create_datetime=datetime(2026, 9, 20, 12, 0, 0),
            )
        )
        await session.commit()

    consumer = InspectingTeamDeleteConsumer(sessions)

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
                    pattern=ExactEventPattern(EventName("contacts_delete")),
                    handler=consumer,
                ),
            ),
            plugins=(),
        )

    runtime = create_application_runtime_components(
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
    await runtime.bootstrap.initialize()

    delete_contacts = DeleteContacts(
        SQLAlchemyUnitOfWorkFactory(sessions),
        runtime.event_publisher,
    )
    result = await delete_contacts.execute(
        ContactDeletionBatch(contact_ids=(1,))
    )

    assert result.contact_ids == (1,)
    assert consumer.contact_existed_during_event is True
    assert len(consumer.seen_payloads) == 1
    assert consumer.seen_payloads[0].contact_ids == (1,)

    async with sessions() as session:
        assert await session.get(WaContactRow, 1) is None

    await engine.dispose()
