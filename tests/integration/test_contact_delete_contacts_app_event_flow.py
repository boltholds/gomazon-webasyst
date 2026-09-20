from datetime import datetime

import pytest
from sqlalchemy import text
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
from gomazon_webasyst.composition.application_runtime import (
    InstalledKnownRuntimeModuleFactories,
    KnownRuntimeModuleFactory,
    ProvidedPluginCatalogSource,
    create_application_runtime_components,
)
from gomazon_webasyst.composition.contacts import create_contacts_runtime_module
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
    "CREATE TABLE contacts_rights (group_id INTEGER NOT NULL, category_id INTEGER NOT NULL, writable INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (group_id, category_id))",
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
async def test_real_contact_delete_runs_installed_contacts_private_rights_handler() -> None:
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
        await session.execute(
            text(
                "INSERT INTO contacts_rights(group_id, category_id, writable) "
                "VALUES (-1, 10, 1), (-2, 10, 1)"
            )
        )
        await session.commit()

    runtime = create_application_runtime_components(
        installed_applications=InMemoryInstalledApplicationCatalog(
            (_app("contacts"),)
        ),
        plugin_source=ProvidedPluginCatalogSource(
            InMemoryInstalledPluginCatalog(())
        ),
        module_source=InstalledKnownRuntimeModuleFactories(
            (
                KnownRuntimeModuleFactory(
                    app_id=AppId("contacts"),
                    build=lambda _event_publisher: (
                        create_contacts_runtime_module(sessions)
                    ),
                ),
            )
        ),
    )
    await runtime.bootstrap.initialize()

    result = await DeleteContacts(
        SQLAlchemyUnitOfWorkFactory(sessions),
        runtime.event_publisher,
    ).execute(ContactDeletionBatch(contact_ids=(1,)))

    assert result.contact_ids == (1,)
    async with sessions() as session:
        assert await session.get(WaContactRow, 1) is None
        rows = await session.execute(
            text(
                "SELECT group_id, category_id "
                "FROM contacts_rights ORDER BY group_id"
            )
        )
        assert [tuple(row) for row in rows] == [(-2, 10)]

    await engine.dispose()
