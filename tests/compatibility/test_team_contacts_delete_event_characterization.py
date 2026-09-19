from pathlib import Path


RELEASE_SHA = "39c267a2fabfb0cd6d94f4dd86b23b4750328dd5"
ROOT = Path(__file__).resolve().parents[2]
FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "webasyst_4_2"
    / "team"
    / "contacts_delete_event.txt"
)
CHARACTERIZATION = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-09-20-team-contacts-delete-event-characterization.md"
)


def test_team_contacts_delete_characterization_is_release_pinned() -> None:
    fixture = FIXTURE.read_text(encoding="utf-8")
    document = CHARACTERIZATION.read_text(encoding="utf-8")
    assert f"SOURCE_COMMIT: {RELEASE_SHA}" in fixture
    assert RELEASE_SHA in document


def test_team_contacts_delete_relay_contract_is_pinned() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    for expected in (
        "handler_app_id = team",
        "source_app_id = contacts",
        "source_event = delete",
        "params_by_reference = true",
        "nested_system = team",
        "nested_event = contacts_delete",
        "nested_result_returned_by_handler = false",
        "nested_event_key = team.contacts_delete",
        "same_payload_object = true",
        "outer_result = no_result",
    ):
        assert expected in text
