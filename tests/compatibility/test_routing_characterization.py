from gomazon_webasyst.compatibility.webasyst.routing.legacy_parser import (
    parse_app_routes,
    parse_system_routes,
)


def test_waRouting_formatRoutes_preserves_rule_iteration_order() -> None:
    """Characterizes Webasyst 4.2.0 waRouting::formatRoutes()."""
    table = parse_system_routes(
        {
            "default": {
                "a/*": "site/frontend",
                "named": {"url": "b/*", "app": "blog"},
                "c/*": "photos/frontend",
            }
        }
    )
    assert [rule.pattern.source for rule in table.routes["default"]] == [
        "a/*",
        "b/*",
        "c/*",
    ]


def test_waRouting_formatRoutes_injects_app_id_for_app_routes() -> None:
    """Characterizes the `$app_id` branch of waRouting::formatRoutes()."""
    rules = parse_app_routes("blog", {"post/*": {"module": "frontend", "action": "post"}})
    assert rules[0].app == "blog"
