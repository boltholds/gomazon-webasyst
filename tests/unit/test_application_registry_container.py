import pytest

from gomazon_webasyst.composition.container import (
    create_container_with_application_catalog,
)
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
)
from gomazon_webasyst.infrastructure.oauth_authorization.app_catalog import (
    InstalledApplicationOAuthConsentAppCatalog,
)


@pytest.mark.asyncio
async def test_container_shares_one_installed_application_catalog_across_api_and_oauth() -> None:
    catalog = InMemoryInstalledApplicationCatalog(())
    container = create_container_with_application_catalog(
        Settings(database_url="sqlite+aiosqlite:///:memory:"),
        installed_application_catalog=catalog,
    )
    try:
        assert container.installed_application_catalog is catalog
        assert container.api_execution.installed_application_catalog is catalog
        assert isinstance(
            container.oauth_authorization.consent_catalog,
            InstalledApplicationOAuthConsentAppCatalog,
        )
        assert (
            container.oauth_authorization.consent_catalog._installed_applications
            is catalog
        )
    finally:
        await container.close()
