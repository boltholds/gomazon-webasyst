from pathlib import Path

import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.compatibility.webasyst.application_registry.errors import (
    LegacyApplicationConfigError,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.installer_policy import (
    NeverForceInstaller,
    StaticInstallerActivationPolicy,
)
from gomazon_webasyst.infrastructure.application_registry.filesystem_catalog import (
    FilesystemInstalledApplicationCatalog,
)


WEBASYST_MANIFEST = """<?php
return [
    'name' => 'Webasyst',
    'version' => '4.2.0',
    'vendor' => 'webasyst',
    'csrf' => true,
    'header_items' => [
        'settings' => [
            'name' => 'Settings',
            'icon' => 'img/wa-settings/settings.svg',
        ],
    ],
];
"""

SITE_MANIFEST = """<?php
return [
    'name' => 'Site',
    'version' => '3.5.3',
    'vendor' => 'webasyst',
    'icon' => 'img/site.svg',
    'frontend' => true,
];
"""

INSTALLER_MANIFEST = """<?php
return [
    'name' => 'Installer',
    'version' => '4.2.0',
    'vendor' => 'webasyst',
    'icon' => 'img/installer.svg',
];
"""


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _base_root(tmp_path: Path) -> Path:
    root = tmp_path / "webasyst"
    root.mkdir()
    _write(root, "wa-system/webasyst/lib/config/app.php", WEBASYST_MANIFEST)
    return root


@pytest.mark.asyncio
async def test_discovers_enabled_apps_and_forced_webasyst_in_legacy_order(
    tmp_path: Path,
) -> None:
    root = _base_root(tmp_path)
    _write(
        root,
        "wa-config/apps.php",
        "<?php return ['site' => true, 'developer' => false];",
    )
    _write(root, "wa-apps/site/lib/config/app.php", SITE_MANIFEST)

    catalog = FilesystemInstalledApplicationCatalog(
        root,
        installer_policy=NeverForceInstaller(),
    )
    snapshot = await catalog.snapshot()

    assert tuple(app.app_id for app in snapshot.applications) == (
        AppId("site"),
        AppId("webasyst"),
    )


@pytest.mark.asyncio
async def test_enabled_app_with_missing_manifest_is_omitted(tmp_path: Path) -> None:
    root = _base_root(tmp_path)
    _write(
        root,
        "wa-config/apps.php",
        "<?php return ['ghost' => true];",
    )

    catalog = FilesystemInstalledApplicationCatalog(
        root,
        installer_policy=NeverForceInstaller(),
    )

    assert tuple(
        app.app_id for app in (await catalog.snapshot()).applications
    ) == (AppId("webasyst"),)


@pytest.mark.asyncio
async def test_waid_policy_can_force_enable_installer(tmp_path: Path) -> None:
    root = _base_root(tmp_path)
    _write(root, "wa-config/apps.php", "<?php return ['site' => true];")
    _write(root, "wa-apps/site/lib/config/app.php", SITE_MANIFEST)
    _write(root, "wa-apps/installer/lib/config/app.php", INSTALLER_MANIFEST)

    catalog = FilesystemInstalledApplicationCatalog(
        root,
        installer_policy=StaticInstallerActivationPolicy(True),
    )

    assert tuple(
        app.app_id for app in (await catalog.snapshot()).applications
    ) == (
        AppId("site"),
        AppId("webasyst"),
        AppId("installer"),
    )


@pytest.mark.asyncio
async def test_existing_disabled_installer_keeps_original_position_when_forced(
    tmp_path: Path,
) -> None:
    root = _base_root(tmp_path)
    _write(
        root,
        "wa-config/apps.php",
        "<?php return ['installer' => false, 'site' => true];",
    )
    _write(root, "wa-apps/site/lib/config/app.php", SITE_MANIFEST)
    _write(root, "wa-apps/installer/lib/config/app.php", INSTALLER_MANIFEST)

    catalog = FilesystemInstalledApplicationCatalog(
        root,
        installer_policy=StaticInstallerActivationPolicy(True),
    )

    assert tuple(
        app.app_id for app in (await catalog.snapshot()).applications
    ) == (
        AppId("installer"),
        AppId("site"),
        AppId("webasyst"),
    )


def test_missing_apps_config_is_startup_configuration_error(tmp_path: Path) -> None:
    root = _base_root(tmp_path)

    with pytest.raises(LegacyApplicationConfigError, match="apps.php"):
        FilesystemInstalledApplicationCatalog(
            root,
            installer_policy=NeverForceInstaller(),
        )


@pytest.mark.parametrize(
    "source",
    [
        "<?php return 'broken';",
        "<?php return some_function();",
    ],
)
def test_malformed_apps_config_fails_catalog_construction(
    tmp_path: Path,
    source: str,
) -> None:
    root = _base_root(tmp_path)
    _write(root, "wa-config/apps.php", source)

    with pytest.raises(ValueError):
        FilesystemInstalledApplicationCatalog(
            root,
            installer_policy=NeverForceInstaller(),
        )


@pytest.mark.asyncio
async def test_catalog_is_startup_snapshot_not_request_time_filesystem_view(
    tmp_path: Path,
) -> None:
    root = _base_root(tmp_path)
    _write(root, "wa-config/apps.php", "<?php return ['site' => true];")
    _write(root, "wa-apps/site/lib/config/app.php", SITE_MANIFEST)

    catalog = FilesystemInstalledApplicationCatalog(
        root,
        installer_policy=NeverForceInstaller(),
    )
    _write(root, "wa-config/apps.php", "<?php return [];")

    assert tuple(
        app.app_id for app in (await catalog.snapshot()).applications
    ) == (
        AppId("site"),
        AppId("webasyst"),
    )


@pytest.mark.asyncio
async def test_unsafe_configured_app_id_fails_discovery(tmp_path: Path) -> None:
    root = _base_root(tmp_path)
    _write(
        root,
        "wa-config/apps.php",
        "<?php return ['../outside' => true];",
    )

    with pytest.raises(ValueError):
        FilesystemInstalledApplicationCatalog(
            root,
            installer_policy=NeverForceInstaller(),
        )
