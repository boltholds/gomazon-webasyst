from gomazon_webasyst.compatibility.webasyst.routing.legacy_parser import (
    AppDispatchRule,
    SystemAppRule,
    SystemRedirectRule,
    parse_app_routes,
    parse_system_routes,
)
from gomazon_webasyst.contracts.routing import (
    ActionSeed,
    ModuleSeed,
    PluginSeed,
)


def test_system_shorthand_maps_first_segment_to_app_and_second_to_module() -> None:
    table = parse_system_routes({"example.com": {"blog/*": "blog/frontend"}})
    rule = table.routes["example.com"][0]
    assert isinstance(rule, SystemAppRule)
    assert rule.app == "blog"
    assert rule.pattern.source == "blog/*"
    assert rule.seed == ModuleSeed(module="frontend")


def test_app_shorthand_maps_first_segment_to_module_and_second_to_action() -> None:
    rules = parse_app_routes("blog", {"rss/": "frontend/rss"})
    rule = rules[0]
    assert isinstance(rule, AppDispatchRule)
    assert rule.pattern.source == "rss/"
    assert rule.seed == ActionSeed(module="frontend", action="rss")


def test_domain_alias_points_to_existing_domain_rules() -> None:
    table = parse_system_routes(
        {
            "example.com": [{"url": "*", "app": "site"}],
            "www.example.com": "example.com",
        }
    )
    assert table.aliases["www.example.com"] == "example.com"
    assert table.routes["www.example.com"] == table.routes["example.com"]


def test_redirect_is_separate_variant_and_302_is_explicit() -> None:
    table = parse_system_routes(
        {"default": [{"url": "old/*", "redirect": "/new/*", "code": 302}]}
    )
    rule = table.routes["default"][0]
    assert isinstance(rule, SystemRedirectRule)
    assert rule.status_code == 302
    assert not hasattr(rule, "app")


def test_route_control_fields_are_removed_from_dynamic_route_data() -> None:
    table = parse_system_routes(
        {
            "default": [
                {
                    "url": "reviews/*",
                    "app": "shop",
                    "plugin": "reviews",
                    "locale": "en_US",
                }
            ]
        }
    )
    rule = table.routes["default"][0]
    assert isinstance(rule, SystemAppRule)
    assert rule.seed == PluginSeed(plugin="reviews")
    assert rule.route_data == {"locale": "en_US"}


def test_temporarily_off_is_preserved_as_rule_state() -> None:
    table = parse_system_routes(
        {"default": [{"url": "hidden/*", "app": "site", "temporarily_off": True}]}
    )
    rule = table.routes["default"][0]
    assert isinstance(rule, SystemAppRule)
    assert rule.temporarily_off is True
