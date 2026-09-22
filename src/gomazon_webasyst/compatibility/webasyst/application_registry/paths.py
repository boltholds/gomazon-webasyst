from pathlib import Path
import re

from gomazon_webasyst.application.access_values import AppId


_SAFE_LEGACY_APP_ID = re.compile(r"^[a-z][a-z0-9_-]*$")


class LegacyApplicationPathError(ValueError):
    """Base error for Webasyst application registry path policy."""


class LegacyApplicationIdRejected(LegacyApplicationPathError):
    """App id cannot safely participate in legacy filesystem discovery."""


class LegacyApplicationPathEscape(LegacyApplicationPathError):
    """Resolved legacy application path escapes the configured Webasyst root."""


class LegacyApplicationPathPolicy:
    def __init__(self, root: Path) -> None:
        canonical = root.resolve(strict=True)
        if not canonical.is_dir():
            raise NotADirectoryError(canonical)
        self._root = canonical

    @property
    def root(self) -> Path:
        return self._root

    def apps_config_path(self) -> Path:
        return self._contained(self._root / "wa-config" / "apps.php")

    def app_manifest_path(self, app_id: AppId) -> Path:
        self._validate_app_id(app_id)
        if app_id.value == "webasyst":
            candidate = (
                self._root
                / "wa-system"
                / "webasyst"
                / "lib"
                / "config"
                / "app.php"
            )
        else:
            candidate = (
                self._root
                / "wa-apps"
                / app_id.value
                / "lib"
                / "config"
                / "app.php"
            )
        return self._contained(candidate)

    def backend_routing_path(self, app_id: AppId) -> Path:
        self._validate_app_id(app_id)
        if app_id.value == "webasyst":
            candidate = (
                self._root
                / "wa-system"
                / "webasyst"
                / "lib"
                / "config"
                / "routing.backend.php"
            )
        else:
            candidate = (
                self._root
                / "wa-apps"
                / app_id.value
                / "lib"
                / "config"
                / "routing.backend.php"
            )
        return self._contained(candidate)

    @staticmethod
    def _validate_app_id(app_id: AppId) -> None:
        if _SAFE_LEGACY_APP_ID.fullmatch(app_id.value) is None:
            raise LegacyApplicationIdRejected(
                f"unsafe legacy application id: {app_id.value!r}"
            )

    def _contained(self, candidate: Path) -> Path:
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self._root):
            raise LegacyApplicationPathEscape(
                f"legacy application path escapes Webasyst root: {resolved}"
            )
        return resolved
