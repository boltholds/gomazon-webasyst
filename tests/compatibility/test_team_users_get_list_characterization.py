from pathlib import Path


RELEASE_SHA = "39c267a2fabfb0cd6d94f4dd86b23b4750328dd5"
ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "webasyst_4_2" / "team" / "users_get_list.txt"
CHARACTERIZATION = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-09-20-team-users-get-list-characterization.md"
)


def test_team_users_get_list_characterization_is_release_pinned() -> None:
    fixture = FIXTURE.read_text(encoding="utf-8")
    document = CHARACTERIZATION.read_text(encoding="utf-8")
    assert f"SOURCE_COMMIT: {RELEASE_SHA}" in fixture
    assert RELEASE_SHA in document


def test_team_users_get_list_selection_and_access_semantics_are_pinned() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    for expected in (
        "method = team.users.getList",
        "http_method = GET",
        "users_requires_login_not_null = true",
        "users_requires_is_user_equal_1 = true",
        "group_collection_requires_is_user_gt_0 = true",
        "group_collection_joins_wa_user_groups = true",
        "scalar_or_list_app_id_defaults_to = limited",
        "requirements_are_AND = true",
        "limited_requires_backend_gte_1 = true",
        "full_requires_backend_gt_1 = true",
        "candidate_access_principals = personal,groups",
        "candidate_access_includes_guest = false",
        "candidate_with_only_hidden_groups_is_hidden = true",
        "visibility_wildcard_does_not_apply_dot_all_fallback = true",
        "final_sort = formatted_name_ASC",
        "online_timeout_seconds = 300",
        "resource_url_prefers_cdn = true",
        "api_environment_photo_retina = false",
        "initial_policy = direct_public_data_url",
    ):
        assert expected in text


def test_team_users_get_list_projection_fields_are_pinned() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    assert (
        "fields = id,name,firstname,lastname,middlename,company,login,email,phone,"
        "locale,jobtitle,last_datetime,photo_url_16,photo_url_32,photo_url_96,"
        "photo_url_144,_event,birth_day,birth_month,create_datetime,_online_status"
        in text
    )
