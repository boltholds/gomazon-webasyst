from pathlib import Path


RELEASE_SHA = "39c267a2fabfb0cd6d94f4dd86b23b4750328dd5"
ROOT = Path(__file__).resolve().parents[2]
FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "webasyst_4_2"
    / "contacts"
    / "delete_flow.txt"
)
CHARACTERIZATION = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-09-20-contact-delete-characterization.md"
)


def test_contact_delete_characterization_is_release_pinned() -> None:
    fixture = FIXTURE.read_text(encoding="utf-8")
    document = CHARACTERIZATION.read_text(encoding="utf-8")
    assert f"SOURCE_COMMIT: {RELEASE_SHA}" in fixture
    assert RELEASE_SHA in document


def test_contact_delete_source_sequence_and_quirks_are_pinned() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    expected = (
        "scalar_id_normalized_to_array_before_event = true",
        "event_app_id = contacts",
        "event_name = delete",
        "event_before_cleanup = true",
        "event_params_by_reference = true",
        "cleanup_01 = wa_contact_rights negative principal ids",
        "cleanup_03 = verification assets by email and wa_contact_data values",
        "cleanup_10 = wa_contact_categories and category counters",
        "cleanup_12 = company_contact_id references set to zero",
        "cleanup_13 = wa_contact rows",
        "semantic_missing_result = false",
        "zero_remaining_members_keeps_previous_counter = true",
        "wa_contact_auths = true",
        "wa_api_tokens = true",
        "destructive_target_mutable_by_event_handler = false",
    )
    positions = [text.index(item) for item in expected[:9]]
    assert positions == sorted(positions)
    for item in expected[9:]:
        assert item in text
