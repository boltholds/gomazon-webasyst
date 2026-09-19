from pathlib import Path

from gomazon_webasyst.compatibility.webasyst.application_registry.config_parser import (
    parse_php_return_value,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.php_values import (
    PhpArray,
)


RELEASE_SHA = "39c267a2fabfb0cd6d94f4dd86b23b4750328dd5"
ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "webasyst_4_2" / "runtime_events_plugins"
CHARACTERIZATION = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-09-19-application-runtime-events-plugins-characterization.md"
)


def test_characterization_is_pinned_to_exact_webasyst_4_2_release() -> None:
    text = CHARACTERIZATION.read_text(encoding="utf-8")
    assert RELEASE_SHA in text
    assert "Webasyst Framework v.4.2.0" in text


def test_plugin_manifest_fixtures_are_source_reduced_and_parse_declaratively() -> None:
    for name in ("plugin_simple_handlers.php", "plugin_wildcard_cross_app.php"):
        source = (FIXTURES / name).read_text(encoding="utf-8")
        assert f"SOURCE_COMMIT: {RELEASE_SHA}" in source
        assert "FIXTURE_KIND: source-reduced" in source
        assert isinstance(parse_php_return_value(source), PhpArray)


def test_plugin_enablement_fixture_pins_truthy_and_falsy_entries() -> None:
    source = (FIXTURES / "plugins_enabled_disabled.php").read_text(encoding="utf-8")
    assert f"SOURCE_COMMIT: {RELEASE_SHA}" in source
    assert "'enabled_plugin' => true" in source
    assert "'numeric_enabled' => 1" in source
    assert "'disabled_plugin' => false" in source
    assert "'numeric_disabled' => 0" in source
    assert isinstance(parse_php_return_value(source), PhpArray)


def test_app_handler_filename_characterization_forbids_runtime_class_derivation() -> None:
    text = (FIXTURES / "app_handler_filename.txt").read_text(encoding="utf-8")
    assert "contacts.delete.handler.php" in text
    assert "event_app_id = contacts" in text
    assert "event_name = delete" in text
    assert "handler_app_id = team" in text
    assert "must not derive/import a class" in text


def test_event_bucket_order_is_pinned() -> None:
    text = (FIXTURES / "event_bucket_order.txt").read_text(encoding="utf-8")
    expected = (
        "1. exact event_app_id + exact event name",
        "2. exact event_app_id + wildcard/masked event bucket",
        "3. wildcard event_app_id + exact event name",
        "4. wildcard event_app_id + wildcard/masked event bucket",
    )
    positions = [text.index(item) for item in expected]
    assert positions == sorted(positions)


def test_cross_app_plugin_subscription_is_source_backed() -> None:
    source = (FIXTURES / "plugin_wildcard_cross_app.php").read_text(encoding="utf-8")
    assert "'event_app_id' => 'webasyst'" in source
    assert "'event_app_id' => 'shop'" in source
    assert "'event_app_id' => 'site'" in source
