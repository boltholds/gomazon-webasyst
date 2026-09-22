import pytest

from gomazon_webasyst.compatibility.webasyst.dispatch.registry import (
    InMemoryDispatchRegistry,
)
from gomazon_webasyst.compatibility.webasyst.dispatch.resolver import (
    DispatchResolver,
)
from gomazon_webasyst.compatibility.webasyst.dispatch.strategies import (
    DispatchStrategyRegistry,
)
from gomazon_webasyst.compatibility.webasyst.routing.app_resolver import (
    AppRouteResolver,
)
from gomazon_webasyst.compatibility.webasyst.routing.backend_app_resolver import (
    BackendAppRouteResolver,
)
from gomazon_webasyst.compatibility.webasyst.routing.backend_resolver import (
    BackendRouteResolver,
)
from gomazon_webasyst.compatibility.webasyst.routing.errors import RouteNotFound
from gomazon_webasyst.compatibility.webasyst.routing.legacy_parser import (
    parse_app_routes,
    parse_system_routes,
)
from gomazon_webasyst.compatibility.webasyst.routing.system_resolver import (
    SystemRouteResolver,
)
from gomazon_webasyst.compatibility.webasyst.service import (
    LegacyCompatibilityService,
)
from gomazon_webasyst.contracts.dispatch import (
    ActionHandlerKey,
    AppNamespace,
)
from gomazon_webasyst.contracts.routing import BackendRouteRequest


def _service():
    registry = InMemoryDispatchRegistry()
    for module, action, handler_id in (
        ("group", "manage", "group-manage"),
        ("profile", "edit", "profile-edit"),
        ("users", "list", "users-list"),
    ):
        registry.register_action(
            ActionHandlerKey(
                namespace=AppNamespace(app="team"),
                module=module,
                action=action,
            ),
            handler_id,
        )

    routes = parse_app_routes(
        "team",
        {
            "u/<login>/?": "profile/",
            "group/<id>/manage/": "group/manage",
            "": "users/",
        },
    )
    return LegacyCompatibilityService(
        system_resolver=SystemRouteResolver(parse_system_routes({})),
        app_resolver=AppRouteResolver(),
        backend_resolver=BackendRouteResolver(),
        app_routes={},
        strategies=DispatchStrategyRegistry(DispatchResolver(registry)),
        backend_app_resolver=BackendAppRouteResolver(),
        backend_routes={"team": routes},
    )


def test_backend_path_route_precedes_query_action_but_keeps_it_when_missing() -> None:
    outcome = _service().resolve_backend(
        BackendRouteRequest(
            app="team",
            path="u/alice/",
            query={"action": "edit"},
        )
    )

    assert outcome.target.handler_id == "profile-edit"
    assert outcome.dispatch.route_data == {"login": "alice"}


def test_explicit_route_action_overrides_backend_query_controls() -> None:
    outcome = _service().resolve_backend(
        BackendRouteRequest(
            app="team",
            path="group/7/manage/",
            query={"action": "list"},
        )
    )

    assert outcome.target.handler_id == "group-manage"
    assert outcome.dispatch.route_data == {"id": "7"}


def test_non_empty_query_module_skips_backend_route_table() -> None:
    outcome = _service().resolve_backend(
        BackendRouteRequest(
            app="team",
            path="group/7/manage/",
            query={"module": "users", "action": "list"},
        )
    )

    assert outcome.target.handler_id == "users-list"
    assert outcome.dispatch.route_data == {}


def test_active_backend_route_table_miss_does_not_fall_back_to_backend() -> None:
    with pytest.raises(RouteNotFound):
        _service().resolve_backend(
            BackendRouteRequest(
                app="team",
                path="missing/path/",
                query={},
            )
        )
