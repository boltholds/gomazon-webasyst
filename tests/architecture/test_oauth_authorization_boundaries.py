from pathlib import Path


APPLICATION = Path("src/gomazon_webasyst/application/oauth_authorization")
OAUTH_SURFACE = (
    APPLICATION,
    Path("src/gomazon_webasyst/compatibility/webasyst/oauth"),
    Path("src/gomazon_webasyst/presentation/http/legacy_oauth.py"),
    Path("src/gomazon_webasyst/composition/oauth_authorization.py"),
)
MAIN = Path("src/gomazon_webasyst/main.py")
MODELS = Path("src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/models.py")


def _sources(root: Path) -> list[tuple[Path, str]]:
    if root.is_file():
        return [(root, root.read_text(encoding="utf-8"))]
    return [
        (path, path.read_text(encoding="utf-8"))
        for path in root.rglob("*.py")
    ]


def test_oauth_application_has_no_transport_html_cookie_or_dynamic_loading_leaks() -> None:
    forbidden = (
        "gomazon_session",
        "auth_token",
        "PHPSESSID",
        "set_cookie",
        "delete_cookie",
        "<form",
        "<html",
        "import_module(",
        "__import__(",
    )
    violations: list[str] = []
    for path, source in _sources(APPLICATION):
        for token in forbidden:
            if token in source:
                violations.append(f"{path}:{token}")
    assert violations == []


def test_oauth_surface_does_not_expand_into_out_of_scope_protocols() -> None:
    forbidden = (
        "token-headless",
        "code_challenge",
        "code_verifier",
        "refresh_token",
        "refresh-token",
        "openid",
        "oidc",
        "PHPSESSID",
    )
    violations: list[str] = []
    for root in OAUTH_SURFACE:
        for path, source in _sources(root):
            lowered = source.lower()
            for token in forbidden:
                if token.lower() in lowered:
                    violations.append(f"{path}:{token}")
    assert violations == []


def test_no_oauth_client_persistence_model_is_introduced() -> None:
    source = MODELS.read_text(encoding="utf-8")
    assert "wa_api_clients" not in source
    assert "OAuthClientRow" not in source
    assert "WaOAuthClientRow" not in source


def test_oauth_static_routes_are_mounted_before_generic_api_catch_all() -> None:
    source = MAIN.read_text(encoding="utf-8")
    oauth = source.index(
        "create_legacy_oauth_router(container.oauth_authorization)"
    )
    generic = source.index(
        "create_legacy_api_router(container.api_execution)"
    )
    assert oauth < generic


def test_oauth_application_does_not_encode_http_route_paths() -> None:
    violations: list[str] = []
    for path, source in _sources(APPLICATION):
        if "/api.php/" in source:
            violations.append(str(path))
    assert violations == []
