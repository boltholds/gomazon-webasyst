from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.compatibility.webasyst.application_registry.config_parser import (
    parse_php_return_value,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.paths import (
    LegacyApplicationPathPolicy,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.php_values import (
    PhpArray,
    PhpArrayAutoKey,
    PhpArrayIntKey,
    PhpArrayStringKey,
    PhpNull,
    PhpValue,
)
from gomazon_webasyst.compatibility.webasyst.routing.legacy_parser import (
    AppDispatchRule,
    RawRouteCollection,
    parse_app_routes,
)


@dataclass(slots=True, frozen=True)
class BackendRoutesMissing:
    app_id: AppId


@dataclass(slots=True, frozen=True)
class BackendRoutesLoaded:
    app_id: AppId
    routes: tuple[AppDispatchRule, ...]


BackendRouteCatalogLookup: TypeAlias = BackendRoutesMissing | BackendRoutesLoaded


class FilesystemBackendRouteCatalog:
    def __init__(self, webasyst_root: Path) -> None:
        self._paths = LegacyApplicationPathPolicy(webasyst_root)

    def resolve(self, app_id: AppId) -> BackendRouteCatalogLookup:
        path = self._paths.backend_routing_path(app_id)
        if not path.is_file():
            return BackendRoutesMissing(app_id)

        parsed = parse_php_return_value(path.read_text(encoding="utf-8"))
        raw = _php_route_collection(parsed)
        return BackendRoutesLoaded(
            app_id=app_id,
            routes=parse_app_routes(app_id.value, raw),
        )


def _php_route_collection(value: PhpValue) -> RawRouteCollection:
    converted = _php_value(value)
    if isinstance(converted, dict | list):
        return converted
    raise TypeError("routing.backend.php must return a PHP array")


def _php_value(value: PhpValue):
    if isinstance(value, PhpNull):
        return None
    if not isinstance(value, PhpArray):
        return value

    if all(isinstance(entry.key, PhpArrayAutoKey) for entry in value.entries):
        return [_php_value(entry.value) for entry in value.entries]

    result: dict[str | int, object] = {}
    next_auto_key = 0
    for entry in value.entries:
        if isinstance(entry.key, PhpArrayStringKey):
            key: str | int = entry.key.value
        elif isinstance(entry.key, PhpArrayIntKey):
            key = entry.key.value
        else:
            while next_auto_key in result:
                next_auto_key += 1
            key = next_auto_key
            next_auto_key += 1
        result[key] = _php_value(entry.value)
        if isinstance(key, int) and key >= next_auto_key:
            next_auto_key = key + 1
    return result
