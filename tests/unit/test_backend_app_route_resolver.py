from gomazon_webasyst.compatibility.webasyst.routing.backend_app_resolver import (
    BackendAppRouteMatched,
    BackendAppRouteNotMatched,
    BackendAppRouteResolver,
)
from gomazon_webasyst.compatibility.webasyst.routing.legacy_parser import (
    parse_app_routes,
)
from gomazon_webasyst.contracts.routing import ActionSeed, ModuleSeed


def _rules():
    return parse_app_routes(
        "team",
        {
            "u/<login>/<tab>/?": "profile/",
            "group/<id>/manage/": "group/manage",
            "": "users/",
        },
    )


def test_backend_app_route_captures_data_and_explicit_module() -> None:
    result = BackendAppRouteResolver().resolve(
        "u/alice/info/",
        _rules(),
    )

    assert isinstance(result, BackendAppRouteMatched)
    assert isinstance(result.seed, ModuleSeed)
    assert result.seed.module == "profile"
    assert result.route_data == {
        "login": "alice",
        "tab": "info",
    }


def test_backend_app_route_can_supply_action_and_capture_id() -> None:
    result = BackendAppRouteResolver().resolve(
        "group/7/manage/",
        _rules(),
    )

    assert isinstance(result, BackendAppRouteMatched)
    assert isinstance(result.seed, ActionSeed)
    assert result.seed.module == "group"
    assert result.seed.action == "manage"
    assert result.route_data == {"id": "7"}


def test_empty_route_matches_backend_app_root() -> None:
    result = BackendAppRouteResolver().resolve("", _rules())

    assert isinstance(result, BackendAppRouteMatched)
    assert isinstance(result.seed, ModuleSeed)
    assert result.seed.module == "users"


def test_unmatched_backend_path_is_explicit() -> None:
    result = BackendAppRouteResolver().resolve("missing/path/", _rules())

    assert isinstance(result, BackendAppRouteNotMatched)
