from pathlib import Path

from gomazon_webasyst.compatibility.webasyst.application_registry.config_parser import (
    parse_php_return_value,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.php_values import PhpArray


RELEASE_SHA = "39c267a2fabfb0cd6d94f4dd86b23b4750328dd5"
ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "webasyst_4_2" / "team_directory"
DOC = ROOT / "docs" / "superpowers" / "specs" / "2026-09-20-team-directory-read-characterization.md"


def test_team_characterization_is_pinned_to_exact_release() -> None:
    assert RELEASE_SHA in DOC.read_text(encoding="utf-8")
    for name in (
        "team_users_get_list.php",
        "team_groups_get_list.php",
        "team_contacts_collection_bridge.php",
    ):
        assert f"SOURCE_COMMIT: {RELEASE_SHA}" in (FIXTURES / name).read_text(encoding="utf-8")


def test_team_api_source_reduced_configs_parse_with_existing_safe_parser() -> None:
    for name in ("team_users_get_list.php", "team_groups_get_list.php"):
        assert isinstance(
            parse_php_return_value((FIXTURES / name).read_text(encoding="utf-8")),
            PhpArray,
        )


def test_keep_visible_fixture_pins_negative_group_semantics() -> None:
    text = (FIXTURES / "team_keep_visible.txt").read_text(encoding="utf-8")
    assert "Self: always visible." in text
    assert "Non-self user with no groups: visible." in text
    assert "effective value < 0" in text
    assert "every target group is hidden: omit user" in text


def test_contacts_collection_bridge_is_nested_team_event() -> None:
    text = (FIXTURES / "team_contacts_collection_bridge.php").read_text(encoding="utf-8")
    assert "wa('team')->event('contacts_collection', $params)" in text
    assert "return !!" in text
