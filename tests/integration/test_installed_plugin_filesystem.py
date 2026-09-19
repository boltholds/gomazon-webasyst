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
from gomazon_webasyst.application.plugins.vo.identity import PluginId, PluginKey
from gomazon_webasyst.application.ports.installed_application_catalog import (
    InstalledApplicationSnapshot,
)
from gomazon_webasyst.application.ports.installed_plugin_catalog import (
    InstalledPluginMissing,
    InstalledPluginResolved,
)
from gomazon_webasyst.infrastructure.plugins.filesystem_catalog import (
    FilesystemInstalledPluginCatalog,
)


def _app(app_id: str) -> InstalledApplication:
    return InstalledApplication(
        app_id=AppId(app_id),
        display_name=ApplicationDisplayName(app_id.title()),
        icons=ApplicationIconSet(()),
        vendor=ApplicationVendor("webasyst"),
        version=ApplicationVersion("1.0.0"),
        capabilities=ApplicationCapabilities(frozenset()),
        header_items=ApplicationHeaderItems(()),
    )


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.mark.asyncio
async def test_discovers_enabled_plugins_in_config_order_and_skips_missing_manifest(
    tmp_path: Path,
) -> None:
    root = tmp_path / "webasyst"
    root.mkdir()
    _write(
        root,
        "wa-config/apps/site/plugins.php",
        "<?php return ['one' => true, 'off' => false, 'ghost' => true, 'two' => 1];",
    )
    _write(
        root,
        "wa-apps/site/plugins/one/lib/config/plugin.php",
        "<?php return ['name' => 'One', 'vendor' => 'example'];",
    )
    _write(
        root,
        "wa-apps/site/plugins/two/lib/config/plugin.php",
        "<?php return ['name' => 'Two', 'vendor' => 'example'];",
    )
    catalog = FilesystemInstalledPluginCatalog(
        root,
        InstalledApplicationSnapshot((_app("site"), _app("webasyst"))),
    )

    snapshot = await catalog.for_application(AppId("site"))
    assert tuple(plugin.key.plugin_id for plugin in snapshot.plugins) == (
        PluginId("one"),
        PluginId("two"),
    )
    assert isinstance(
        await catalog.resolve(PluginKey(AppId("site"), PluginId("one"))),
        InstalledPluginResolved,
    )
    assert isinstance(
        await catalog.resolve(PluginKey(AppId("site"), PluginId("off"))),
        InstalledPluginMissing,
    )


@pytest.mark.asyncio
async def test_missing_plugins_file_is_empty_snapshot(tmp_path: Path) -> None:
    root = tmp_path / "webasyst"
    root.mkdir()
    catalog = FilesystemInstalledPluginCatalog(
        root,
        InstalledApplicationSnapshot((_app("blog"),)),
    )
    snapshot = await catalog.for_application(AppId("blog"))
    assert snapshot.plugins == ()


@pytest.mark.asyncio
async def test_system_webasyst_app_is_not_scanned_as_ordinary_plugin_host(
    tmp_path: Path,
) -> None:
    root = tmp_path / "webasyst"
    root.mkdir()
    _write(
        root,
        "wa-config/apps/webasyst/plugins.php",
        "<?php return ['should_not_load' => true];",
    )
    _write(
        root,
        "wa-apps/webasyst/plugins/should_not_load/lib/config/plugin.php",
        "<?php return ['name' => 'No', 'vendor' => 'example'];",
    )
    catalog = FilesystemInstalledPluginCatalog(
        root,
        InstalledApplicationSnapshot((_app("webasyst"),)),
    )
    assert (await catalog.for_application(AppId("webasyst"))).plugins == ()
