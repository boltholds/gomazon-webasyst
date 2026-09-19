from pathlib import Path


RELEASE_SHA = "39c267a2fabfb0cd6d94f4dd86b23b4750328dd5"
ROOT = Path(__file__).resolve().parents[2]
FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "webasyst_4_2"
    / "team"
    / "groups_get_list.txt"
)
CHARACTERIZATION = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-09-20-team-groups-get-list-characterization.md"
)


def test_team_groups_characterization_is_pinned_to_exact_release() -> None:
    fixture = FIXTURE.read_text(encoding="utf-8")
    document = CHARACTERIZATION.read_text(encoding="utf-8")
    assert f"SOURCE_COMMIT: {RELEASE_SHA}" in fixture
    assert RELEASE_SHA in document


def test_team_groups_source_contract_is_pinned() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    for expected in (
        "target = team.groups.getList",
        "default_http_method = GET",
        "response_fields = id,name,cnt,type,description",
        "excluded_fields = icon,sort",
        "order_by = sort",
        "type_filter = filter[type]",
        "visibility_right_prefix = manage_users_in_group.",
        "visibility_operator = >=",
        "visibility_threshold = 0",
        "version = 2.3.4",
        "type_filter_scalar_trim = true",
        "explicit_empty_scalar = one_empty_string_item",
        "missing_filter_type = no_type_filter",
    ):
        assert expected in text
