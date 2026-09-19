from pathlib import Path

import pytest

from gomazon_webasyst.compatibility.webasyst.application_registry.config_parser import (
    LegacyPhpConfigError,
    parse_php_return_value,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.php_values import PhpArray


RELEASE_SHA = "39c267a2fabfb0cd6d94f4dd86b23b4750328dd5"
ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "webasyst_4_2" / "application_registry"
CHARACTERIZATION = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-09-19-installed-application-registry-characterization.md"
)

SOURCE_REDUCED = {
    "app_scalar_icon.php",
    "app_img_fallback.php",
    "app_header_items.php",
    "webasyst_app.php",
}
SYNTHETIC = {
    "apps_enabled_disabled.php",
    "app_icon_map.php",
    "unsupported_dynamic.php",
}


def test_characterization_is_pinned_to_exact_4_2_0_release_commit() -> None:
    text = CHARACTERIZATION.read_text(encoding="utf-8")
    assert RELEASE_SHA in text
    assert "Webasyst Framework v.4.2.0" in text


def test_source_reduced_fixtures_record_provenance() -> None:
    for name in SOURCE_REDUCED:
        text = (FIXTURE_DIR / name).read_text(encoding="utf-8")
        assert f"SOURCE_COMMIT: {RELEASE_SHA}" in text
        assert "FIXTURE_KIND: source-reduced" in text


def test_synthetic_fixtures_are_explicitly_not_claimed_as_verbatim_source() -> None:
    for name in SYNTHETIC:
        text = (FIXTURE_DIR / name).read_text(encoding="utf-8")
        assert f"SOURCE_COMMIT: {RELEASE_SHA}" in text
        assert "FIXTURE_KIND: synthetic" in text


def test_fixture_set_covers_both_php_array_syntaxes() -> None:
    long_form = (FIXTURE_DIR / "app_scalar_icon.php").read_text(encoding="utf-8")
    short_form = (FIXTURE_DIR / "app_img_fallback.php").read_text(encoding="utf-8")
    assert "return array(" in long_form
    assert "return [" in short_form


def test_security_fixture_contains_dynamic_expression_for_future_fail_closed_parser() -> None:
    text = (FIXTURE_DIR / "unsupported_dynamic.php").read_text(encoding="utf-8")
    assert "strtoupper(" in text
    assert "synthetic-security-case" in text


@pytest.mark.parametrize(
    "name",
    sorted(SOURCE_REDUCED | {"apps_enabled_disabled.php", "app_icon_map.php"}),
)
def test_characterized_declarative_fixtures_parse_without_php_execution(name: str) -> None:
    value = parse_php_return_value((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    assert isinstance(value, PhpArray)


def test_characterized_dynamic_fixture_fails_closed() -> None:
    with pytest.raises(LegacyPhpConfigError):
        parse_php_return_value(
            (FIXTURE_DIR / "unsupported_dynamic.php").read_text(encoding="utf-8")
        )
