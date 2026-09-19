from pathlib import Path

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.ports.installed_application_catalog import (
    InstalledApplicationResolution,
    InstalledApplicationSnapshot,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.config_parser import (
    DEFAULT_MAX_BYTES,
    LegacyPhpConfigError,
    LegacyPhpConfigLimitError,
    parse_php_return_value,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.errors import (
    LegacyApplicationConfigError,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.installer_policy import (
    LegacyInstallerActivationPolicy,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.normalizer import (
    normalize_application_manifest,
    normalize_configured_app_mapping,
    php_truthy,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.paths import (
    LegacyApplicationPathPolicy,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.raw_config import (
    php_string_mapping,
)
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
)


class FilesystemInstalledApplicationCatalog:
    def __init__(
        self,
        root: Path,
        *,
        installer_policy: LegacyInstallerActivationPolicy,
    ) -> None:
        paths = LegacyApplicationPathPolicy(root)
        apps_config_path = paths.apps_config_path()
        if not apps_config_path.is_file():
            raise LegacyApplicationConfigError(
                f"File wa-config/apps.php not found: {apps_config_path}"
            )

        configured_value = _parse_file(apps_config_path)
        configured = php_string_mapping(
            configured_value,
            context="wa-config/apps.php",
        )

        # Exact waSystem::getApps() order: force webasyst first, then evaluate
        # the optional WAID Installer auto-enable branch.
        configured["webasyst"] = True
        installer_enabled = (
            "installer" in configured and php_truthy(configured["installer"])
        )
        if (
            not installer_enabled
            and installer_policy.should_force_enable()
        ):
            configured["installer"] = True

        applications = []
        for app_id in normalize_configured_app_mapping(configured):
            manifest_path = paths.app_manifest_path(app_id)
            if not manifest_path.is_file():
                # Webasyst 4.2.0 skips enabled entries whose app.php is absent.
                continue
            manifest = _parse_file(manifest_path)
            applications.append(
                normalize_application_manifest(app_id, manifest)
            )

        self._catalog = InMemoryInstalledApplicationCatalog(
            tuple(applications)
        )

    async def resolve(
        self,
        app_id: AppId,
    ) -> InstalledApplicationResolution:
        return await self._catalog.resolve(app_id)

    async def snapshot(self) -> InstalledApplicationSnapshot:
        return await self._catalog.snapshot()


def _parse_file(path: Path):
    try:
        size = path.stat().st_size
    except OSError:
        raise

    if size > DEFAULT_MAX_BYTES:
        raise LegacyPhpConfigLimitError(
            f"PHP config byte budget exceeded before read: {path}"
        )

    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        raise

    try:
        return parse_php_return_value(source)
    except LegacyPhpConfigError:
        raise
