from pathlib import Path
import re

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.plugins.vo.identity import PluginId
from gomazon_webasyst.compatibility.webasyst.application_registry.paths import (
    LegacyApplicationPathPolicy,
)


_SAFE_LEGACY_PLUGIN_ID = re.compile(r"^[a-z][a-z0-9_-]*$")


class LegacyPluginPathError(ValueError):
    pass


class LegacyPluginIdRejected(LegacyPluginPathError):
    pass


class LegacyPluginPathEscape(LegacyPluginPathError):
    pass


class LegacyPluginPathPolicy:
    def __init__(self, root: Path) -> None:
        app_paths = LegacyApplicationPathPolicy(root)
        self._root = app_paths.root
        self._app_paths = app_paths

    def plugins_config_path(self, app_id: AppId) -> Path:
        self._app_paths._validate_app_id(app_id)
        return self._contained(
            self._root / "wa-config" / "apps" / app_id.value / "plugins.php"
        )

    def plugin_manifest_path(
        self,
        app_id: AppId,
        plugin_id: PluginId,
    ) -> Path:
        self._app_paths._validate_app_id(app_id)
        self._validate_plugin_id(plugin_id)
        return self._contained(
            self._root
            / "wa-apps"
            / app_id.value
            / "plugins"
            / plugin_id.value
            / "lib"
            / "config"
            / "plugin.php"
        )

    @staticmethod
    def _validate_plugin_id(plugin_id: PluginId) -> None:
        if _SAFE_LEGACY_PLUGIN_ID.fullmatch(plugin_id.value) is None:
            raise LegacyPluginIdRejected(
                f"unsafe legacy plugin id: {plugin_id.value!r}"
            )

    def _contained(self, candidate: Path) -> Path:
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self._root):
            raise LegacyPluginPathEscape(
                f"legacy plugin path escapes Webasyst root: {resolved}"
            )
        return resolved
