from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_team_invitation_application_stays_framework_independent() -> None:
    source = (
        ROOT / "src" / "gomazon_webasyst" / "application" / "team" / "invitation.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "sqlalchemy",
        "fastapi",
        "gomazon_webasyst.infrastructure",
        "gomazon_webasyst.compatibility",
    ):
        assert forbidden not in source


def test_wa_app_tokens_is_runtime_private_not_generic_orm() -> None:
    models = (
        ROOT
        / "src"
        / "gomazon_webasyst"
        / "infrastructure"
        / "persistence"
        / "sqlalchemy"
        / "models.py"
    ).read_text(encoding="utf-8")
    invitation = (
        ROOT
        / "src"
        / "gomazon_webasyst"
        / "infrastructure"
        / "team"
        / "sqlalchemy"
        / "invitation.py"
    ).read_text(encoding="utf-8")

    assert "class WaAppTokenRow" not in models
    assert '"wa_app_tokens"' in invitation
    assert "Table(" in invitation
