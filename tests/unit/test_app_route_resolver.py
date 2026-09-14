from gomazon_webasyst.compatibility.webasyst.routing.app_resolver import AppRouteResolver
from gomazon_webasyst.compatibility.webasyst.routing.legacy_parser import parse_app_routes
from gomazon_webasyst.contracts.dispatch import ActionDispatch, AppNamespace, DefaultDispatch
from gomazon_webasyst.contracts.routing import (
    ActionSeed,
    AnyAppRouteConstraint,
    AppSettlement,
    EmptySeed,
    ModuleRouteConstraint,
    ModuleSeed,
)


def settlement(seed=EmptySeed(), *, constraint=None, route_data=None):
    return AppSettlement(
        app="blog",
        matched_prefix="blog/",
        remaining_path="",
        seed=seed,
        constraint=constraint or AnyAppRouteConstraint(),
        route_data=route_data or {},
    )


def test_empty_seed_and_action_route_resolve_to_action_dispatch() -> None:
    rules = parse_app_routes("blog", {"post/*": "frontend/post"})
    result = AppRouteResolver().resolve(settlement(), "post/42", rules)
    assert result.request == ActionDispatch(
        namespace=AppNamespace(app="blog"), module="frontend", action="post"
    )


def test_parent_explicit_module_restricts_candidate_app_routes() -> None:
    rules = parse_app_routes(
        "blog",
        {
            "post/*": {"module": "backend", "action": "wrong"},
            "*": {"module": "frontend", "action": "right"},
        },
    )
    result = AppRouteResolver().resolve(
        settlement(
            ModuleSeed(module="frontend"),
            constraint=ModuleRouteConstraint(module="frontend"),
        ),
        "post/42",
        rules,
    )
    assert isinstance(result.request, ActionDispatch)
    assert result.request.action == "right"


def test_parent_params_prevent_app_capture_but_app_explicit_data_overrides() -> None:
    rules = parse_app_routes(
        "blog",
        {
            "<locale>/<slug>/": {
                "module": "frontend",
                "action": "post",
                "locale": "de_DE",
            }
        },
    )
    result = AppRouteResolver().resolve(
        settlement(route_data={"locale": "ru_RU"}),
        "en_US/hello/",
        rules,
    )
    assert result.route_data == {"locale": "de_DE", "slug": "hello"}


def test_missing_app_route_falls_back_to_frontend_default_dispatch() -> None:
    result = AppRouteResolver().resolve(settlement(), "unmatched", ())
    assert result.request == DefaultDispatch(
        namespace=AppNamespace(app="blog"), module="frontend"
    )


def test_parent_action_seed_survives_when_no_app_rule_matches() -> None:
    result = AppRouteResolver().resolve(
        settlement(ActionSeed(module="frontend", action="archive")),
        "unmatched",
        (),
    )
    assert result.request == ActionDispatch(
        namespace=AppNamespace(app="blog"), module="frontend", action="archive"
    )
