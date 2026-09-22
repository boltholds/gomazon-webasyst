from pathlib import Path


RELEASE_SHA = "39c267a2fabfb0cd6d94f4dd86b23b4750328dd5"
ROOT = Path(__file__).resolve().parents[2]
FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "webasyst_4_2"
    / "team"
    / "contacts_collection_event.txt"
)
CHARACTERIZATION = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-09-22-team-contacts-collection-event-characterization.md"
)


def test_team_contacts_collection_characterization_is_release_pinned() -> None:
    fixture = FIXTURE.read_text(encoding="utf-8")
    document = CHARACTERIZATION.read_text(encoding="utf-8")
    assert f"SOURCE_COMMIT: {RELEASE_SHA}" in fixture
    assert RELEASE_SHA in document


def test_team_contacts_collection_boolean_result_semantics_are_pinned() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    for expected in (
        "source_app_id = contacts",
        "source_event = contacts_collection",
        "nested_app_id = team",
        "nested_event = contacts_collection",
        "payload_by_reference = true",
        "false_handler_value_is_still_non_null_result = true",
        "outer_handler_always_returns_result = true",
        "outer_false_when_nested_results_empty = true",
        "outer_true_when_nested_results_non_empty = true",
        "nested_failures_without_results_do_not_make_true = true",
    ):
        assert expected in text
