from pathlib import Path


SOURCE_SHA = "dc497e33fb7d33d40c8a897051fa8ed3d2657441"
ROOT = Path(__file__).resolve().parents[2]
FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "webasyst_contacts_1_1_7"
    / "private_rights_delete_event.txt"
)
CHARACTERIZATION = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-09-20-contacts-private-rights-delete-event-characterization.md"
)


def test_contacts_private_rights_characterization_is_app_source_pinned() -> None:
    fixture = FIXTURE.read_text(encoding="utf-8")
    document = CHARACTERIZATION.read_text(encoding="utf-8")
    assert f"SOURCE_COMMIT: {SOURCE_SHA}" in fixture
    assert SOURCE_SHA in document
    assert "APP_VERSION: 1.1.7" in fixture


def test_contacts_delete_private_rights_contract_is_pinned() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    for expected in (
        "source_app_id = contacts",
        "source_event = delete",
        "params_by_reference = true",
        "personal_group_id = negative_integer_contact_id",
        "table = contacts_rights",
        "delete_field = group_id",
        "primary_key = group_id,category_id",
        "contact_ids_remain_positive_in_application",
        "negative_group_id_encoding_is_infrastructure_private",
        "outer_result = no_result",
    ):
        assert expected in text
