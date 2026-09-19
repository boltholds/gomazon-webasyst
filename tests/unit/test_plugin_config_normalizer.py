from pathlib import Path

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.plugins.vo.handlers import (
    PluginHandlerMethodName,
)
from gomazon_webasyst.application.plugins.vo.identity import PluginId, PluginKey
from gomazon_webasyst.application.plugins.vo.metadata import (
    PluginImageMissing,
    PluginImagePresent,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.config_parser import (
    parse_php_return_value,
)
from gomazon_webasyst.compatibility.webasyst.plugins.normalizer import (
    normalize_configured_plugin_ids,
    normalize_plugin_manifest,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "webasyst_4_2" / "runtime_events_plugins"


def _fixture(name: str):
    return parse_php_return_value(
        (FIXTURES / name).read_text(encoding="utf-8")
    )


def test_configured_plugin_ids_follow_php_truth_semantics_and_order() -> None:
    assert normalize_configured_plugin_ids(
        _fixture("plugins_enabled_disabled.php"),
        app_id=AppId("site"),
    ) == (
        PluginId("enabled_plugin"),
        PluginId("numeric_enabled"),
    )


def test_simple_handlers_are_normalized_to_parent_app_subscriptions() -> None:
    plugin = normalize_plugin_manifest(
        PluginKey(AppId("blog"), PluginId("myposts")),
        _fixture("plugin_simple_handlers.php"),
    )
    declarations = plugin.handler_declarations.items
    assert [(d.source_app_id.value, d.event_pattern.value) for d in declarations] == [
        ("blog", "search_posts_backend"),
        ("blog", "backend_sidebar"),
    ]
    assert declarations[0].methods == (PluginHandlerMethodName("postSearch"),)
    assert isinstance(plugin.image, PluginImagePresent)
    assert plugin.image.reference.value == (
        "wa-apps/blog/plugins/myposts//img/myposts.png"
    )


def test_wildcard_handlers_preserve_cross_app_event_sources() -> None:
    plugin = normalize_plugin_manifest(
        PluginKey(AppId("site"), PluginId("rublesign")),
        _fixture("plugin_wildcard_cross_app.php"),
    )
    declarations = plugin.handler_declarations.items
    assert [
        (d.source_app_id.value, d.event_pattern.value, d.methods[0].value)
        for d in declarations
    ] == [
        ("webasyst", "backend_header", "backendHeader"),
        ("shop", "frontend_head", "frontendHead"),
        ("site", "frontend_page", "frontendPage"),
    ]


def test_capabilities_inject_implicit_event_declarations_without_overwriting_explicit() -> None:
    source = """<?php return [
        'name' => 'Demo',
        'vendor' => 'example',
        'rights' => true,
        'frontend' => true,
        'cron' => true,
        'handlers' => [
            'routing' => 'customRouting',
        ],
    ];"""
    plugin = normalize_plugin_manifest(
        PluginKey(AppId("site"), PluginId("demo")),
        parse_php_return_value(source),
    )
    declarations = {
        d.event_pattern.value: tuple(m.value for m in d.methods)
        for d in plugin.handler_declarations.items
    }
    assert declarations["rights.config"] == ("rightsConfig",)
    assert declarations["routing"] == ("customRouting",)
    assert declarations["cron"] == ("cron",)


def test_missing_image_is_explicit_state() -> None:
    plugin = normalize_plugin_manifest(
        PluginKey(AppId("site"), PluginId("noimage")),
        parse_php_return_value(
            "<?php return ['name' => 'No Image', 'vendor' => 'example'];"
        ),
    )
    assert isinstance(plugin.image, PluginImageMissing)
