from pathlib import Path


APPLICATION_FILES = (
    Path("src/gomazon_webasyst/application/api_credentials.py"),
    Path("src/gomazon_webasyst/application/api_token_issuance.py"),
    Path("src/gomazon_webasyst/application/ports/api_credentials.py"),
    Path("src/gomazon_webasyst/application/ports/api_credential_uow.py"),
    Path("src/gomazon_webasyst/application/ports/api_credential_generator.py"),
    Path("src/gomazon_webasyst/application/ports/api_credential_policies.py"),
)


def test_api_credential_application_layer_has_no_framework_or_compatibility_dependencies() -> None:
    forbidden = (
        "fastapi",
        "starlette",
        "sqlalchemy",
        "secrets",
        "gomazon_webasyst.compatibility",
    )

    for path in APPLICATION_FILES:
        source = path.read_text()
        for needle in forbidden:
            assert needle not in source, (path, needle)


def test_api_credential_application_layer_has_no_legacy_storage_names() -> None:
    for path in APPLICATION_FILES:
        source = path.read_text()
        assert "wa_api_tokens" not in source, path
        assert "wa_api_auth_codes" not in source, path
