from pathlib import Path

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
from gomazon_webasyst.composition.backend_routes import (
    create_installed_backend_route_table,
)
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
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


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.mark.asyncio
async def test_installed_backend_routes_load_only_for_canonical_snapshot(
    tmp_path: Path,
) -> None:
    root = tmp_path / "webasyst"
    root.mkdir()
    _write(
        root,
        "wa-apps/team/lib/config/routing.backend.php",
        "<?php return ['' => 'users/'];",
    )
    _write(
        root,
        "wa-apps/not-installed/lib/config/routing.backend.php",
        "<?php return ['' => 'backend/'];",
    )

    result = await create_installed_backend_route_table(
        root,
        InMemoryInstalledApplicationCatalog(
            (_app("team"), _app("crm"))
        ),
    )

    assert tuple(result) == ("team",)
    assert result["team"][0].pattern.source == ""


@pytest.mark.asyncio
async def test_installed_backend_route_table_is_immutable(
    tmp_path: Path,
) -> None:
    root = tmp_path / "webasyst"
    root.mkdir()
    _write(
        root,
        "wa-apps/team/lib/config/routing.backend.php",
        "<?php return ['' => 'users/'];",
    )
    result = await create_installed_backend_route_table(
        root,
        InMemoryInstalledApplicationCatalog((_app("team"),)),
    )

    with pytest.raises(TypeError):
        result["team"] = ()
