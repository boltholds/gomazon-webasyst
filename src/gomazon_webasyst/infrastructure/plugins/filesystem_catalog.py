from pathlib import Path

from gomazon_webasyst.application.application_registry.entities.installed_application import (
    InstalledApplication,
)
from gomazon_webasyst.application.plugins.vo.identity import PluginKey
from gomazon_webasyst.application.ports.installed_application_catalog import (
    InstalledApplicationSnapshot,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.config_parser import (
    DEFAULT_MAX_BYTES,
    LegacyPhpConfigLimitError,
    parse_php_return_value,
)
from gomazon_webasyst.compatibility.webasyst.plugins.normalizer import (
    normalize_configured_plugin_ids,
    normalize_plugin_manifest,
)
from gomazon_webasyst.compatibility.webasyst.plugins.paths import (
    LegacyPluginPathPolicy,
)
from gomazon_webasyst.infrastructure.plugins.in_memory_catalog import (
    InMemoryInstalledPluginCatalog,
)


class FilesystemInstalledPluginCatalog(InMemoryInstalledPluginCatalog):
    def __init__(
        self,
        root: Path,
        applications: InstalledApplicationSnapshot,
    ) -> None:
        paths = LegacyPluginPathPolicy(root)
        plugins = []
        for application in applications.applications:
            if application.app_id.value == "webasyst":
                continue
            plugins.extend(
                _discover_application_plugins(paths, application)
            )
        super().__init__(tuple(plugins))


def _discover_application_plugins(
    paths: LegacyPluginPathPolicy,
    application: InstalledApplication,
):
    config_path = paths.plugins_config_path(application.app_id)
    if not config_path.is_file():
        return ()

    configured = parse_php_return_value(_read_config(config_path))
    plugin_ids = normalize_configured_plugin_ids(
        configured,
        app_id=application.app_id,
    )

    plugins = []
    for plugin_id in plugin_ids:
        manifest_path = paths.plugin_manifest_path(
            application.app_id,
            plugin_id,
        )
        if not manifest_path.is_file():
            continue
        manifest = parse_php_return_value(_read_config(manifest_path))
        plugins.append(
            normalize_plugin_manifest(
                PluginKey(application.app_id, plugin_id),
                manifest,
            )
        )
    return tuple(plugins)


def _read_config(path: Path) -> str:
    size = path.stat().st_size
    if size > DEFAULT_MAX_BYTES:
        raise LegacyPhpConfigLimitError(
            f"PHP config byte budget exceeded before read: {path}"
        )
    return path.read_text(encoding="utf-8")
