import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.composition.application_runtime import (
    create_default_application_runtime_module_factories,
)
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
)


@pytest.mark.asyncio
async def test_default_runtime_factories_include_contacts_and_team() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    factories = create_default_application_runtime_module_factories(
        sessions,
        installed_applications=InMemoryInstalledApplicationCatalog(()),
    )

    assert tuple(factory.app_id.value for factory in factories) == (
        "contacts",
        "team",
    )
    await engine.dispose()
