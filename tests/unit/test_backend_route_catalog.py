from pathlib import Path

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.compatibility.webasyst.routing.backend_catalog import (
    BackendRoutesLoaded,
    BackendRoutesMissing,
    FilesystemBackendRouteCatalog,
)
from gomazon_webasyst.contracts.routing import ActionSeed, ModuleSeed


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_missing_backend_route_file_is_explicit(tmp_path: Path) -> None:
    root = tmp_path / "webasyst"
    root.mkdir()
    catalog = FilesystemBackendRouteCatalog(root)

    result = catalog.resolve(AppId("team"))

    assert isinstance(result, BackendRoutesMissing)


def test_declarative_backend_route_file_loads_ordered_typed_rules(
    tmp_path: Path,
) -> None:
    root = tmp_path / "webasyst"
    root.mkdir()
    _write(
        root,
        "wa-apps/team/lib/config/routing.backend.php",
        """<?php return array(
            'u/<login>/<tab>/?' => 'profile/',
            'calendar/external/authorize/' => array(
                'url' => 'calendar/external/authorize/<id>',
                'module' => 'calendarExternal',
                'action' => 'authorize',
                'authorize_end' => '1',
            ),
            '' => 'users/',
        );""",
    )

    result = FilesystemBackendRouteCatalog(root).resolve(AppId("team"))

    assert isinstance(result, BackendRoutesLoaded)
    assert len(result.routes) == 3
    assert isinstance(result.routes[0].seed, ModuleSeed)
    assert result.routes[0].seed.module == "profile"
    assert isinstance(result.routes[1].seed, ActionSeed)
    assert result.routes[1].seed.module == "calendarExternal"
    assert result.routes[1].seed.action == "authorize"
    assert result.routes[1].route_data == {"authorize_end": "1"}
    assert result.routes[2].pattern.source == ""
    assert isinstance(result.routes[2].seed, ModuleSeed)
    assert result.routes[2].seed.module == "users"
