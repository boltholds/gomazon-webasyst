from pathlib import Path


APPLICATION = Path("src/gomazon_webasyst/application/backend_session_bridge")
AUTH_CONTRACT = Path("src/gomazon_webasyst/contracts/auth.py")
MAIN = Path("src/gomazon_webasyst/main.py")


def test_backend_session_bridge_application_dependency_boundaries() -> None:
    forbidden = (
        "fastapi",
        "starlette",
        "sqlalchemy",
        "gomazon_webasyst.compatibility",
        "gomazon_session",
        "auth_token",
        "PHPSESSID",
        "set_cookie",
        "delete_cookie",
    )
    violations: list[str] = []
    for path in APPLICATION.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in source:
                violations.append(f"{path}:{token}")
    assert violations == []


def test_password_credentials_do_not_gain_remember_transport_state() -> None:
    source = AUTH_CONTRACT.read_text(encoding="utf-8")
    assert "remember:" not in source
    assert "remember :" not in source


def test_bridge_does_not_claim_php_session_interoperability() -> None:
    bridge_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in APPLICATION.rglob("*.py")
    )
    assert "PHPSESSID" not in bridge_sources
    assert "php session" not in bridge_sources.lower()


def test_production_main_does_not_mount_backend_auth_routes() -> None:
    source = MAIN.read_text(encoding="utf-8")
    forbidden = (
        "backend_session_router",
        "create_backend_session_router",
        "login_router",
        "logout_router",
    )
    for token in forbidden:
        assert token not in source
