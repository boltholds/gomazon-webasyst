from pathlib import Path

RELEASE_SHA = "39c267a2fabfb0cd6d94f4dd86b23b4750328dd5"
ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/webasyst_4_2/team/users_invite.txt"


def test_team_users_invite_characterization_is_release_pinned() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    assert f"SOURCE_COMMIT: {RELEASE_SHA}" in text


def test_team_users_invite_semantics_are_pinned() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    for expected in (
        "method=team.users.invite",
        "required_right=team/add_users",
        "type_code_exact=code",
        "manage_right=manage_group.<id>",
        "scalar_dot_all_fallback=true",
        "event=team.invite_user",
        "code_flow_runs_hook=false",
        "existing_non_user_reused=true",
        "table=wa_app_tokens",
        "link_type=user_invite",
        "code_type=waid_invite",
        "ttl_seconds=259200",
        "limit_per_contact_app_type=5",
        "disconnected_code_local_success=true",
        "send_true_omits_link=true",
        "mailer_false_still_success=true",
    ):
        assert expected in text
