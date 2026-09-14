import pytest

from gomazon_webasyst.compatibility.webasyst.routing.errors import RouteNotFound
from gomazon_webasyst.compatibility.webasyst.routing.legacy_parser import parse_system_routes
from gomazon_webasyst.compatibility.webasyst.routing.system_resolver import SystemRouteResolver
from gomazon_webasyst.contracts.routing import (
    ActionSeed,
    AppSettlement,
    FrontendRouteRequest,
    ModuleRouteConstraint,
    RedirectSettlement,
)


def resolve(raw, *, domain="example.com", path="", query=None):
    resolver = SystemRouteResolver(parse_system_routes(raw))
    return resolver.resolve(
        FrontendRouteRequest(domain=domain, path=path, query=query or {})
    )


def test_exact_domain_is_used_before_default() -> None:
    result = resolve(
        {
            "example.com": [{"url": "*", "app": "blog"}],
            "default": [{"url": "*", "app": "site"}],
        },
        path="post/1",
    )
    assert isinstance(result, AppSettlement)
    assert result.app == "blog"


def test_alias_uses_target_domain_routes() -> None:
    result = resolve(
        {
            "example.com": [{"url": "*", "app": "blog"}],
            "www.example.com": "example.com",
        },
        domain="www.example.com",
        path="post/1",
    )
    assert result.app == "blog"


def test_temporarily_off_rule_is_skipped_and_order_is_preserved() -> None:
    result = resolve(
        {
            "default": [
                {"url": "*", "app": "hidden", "temporarily_off": True},
                {"url": "*", "app": "site"},
            ]
        },
        path="x",
    )
    assert result.app == "site"


def test_explicit_route_data_overrides_capture_data() -> None:
    result = resolve(
        {
            "default": [
                {"url": "<locale>/*", "app": "site", "locale": "ru_RU"}
            ]
        },
        path="en_US/page",
    )
    assert result.route_data["locale"] == "ru_RU"


def test_captured_dispatch_controls_become_typed_seed() -> None:
    result = resolve(
        {"default": [{"url": "<module>/<action>/", "app": "blog"}]},
        path="frontend/post/",
    )
    assert result.seed == ActionSeed(module="frontend", action="post")


def test_explicit_module_creates_app_route_constraint() -> None:
    result = resolve(
        {"default": [{"url": "blog/*", "app": "blog", "module": "frontend"}]},
        path="blog/post/",
    )
    assert result.constraint == ModuleRouteConstraint(module="frontend")


def test_redirect_wildcard_interpolation_preserves_query_string() -> None:
    result = resolve(
        {"default": [{"url": "old/*", "redirect": "/new/*", "code": 302}]},
        path="old/a/b",
        query={"x": "1", "y": "two"},
    )
    assert result == RedirectSettlement(
        location="/new/a/b?x=1&y=two",
        status_code=302,
    )


def test_url_is_percent_decoded_before_matching() -> None:
    result = resolve(
        {"default": [{"url": "tag/<slug>/", "app": "blog"}]},
        path="tag/%D1%82%D0%B5%D1%81%D1%82/",
    )
    assert result.route_data["slug"] == "тест"


def test_wildcard_match_redirects_to_more_specific_trailing_slash_route() -> None:
    result = resolve(
        {
            "default": [
                {"url": "news/", "app": "blog"},
                {"url": "*", "app": "site"},
            ]
        },
        path="news",
    )
    assert result == RedirectSettlement(location="/news/", status_code=301)


def test_missing_system_route_raises_route_not_found() -> None:
    with pytest.raises(RouteNotFound):
        resolve({"default": [{"url": "news/", "app": "blog"}]}, path="other")


def test_settlement_carries_remaining_app_path_without_reparsing() -> None:
    result = resolve(
        {"default": [{"url": "blog/*", "app": "blog"}]},
        path="blog/post/42",
    )
    assert result.matched_prefix == "blog/"
    assert result.remaining_path == "post/42"
