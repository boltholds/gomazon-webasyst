from pathlib import Path


CONTRACT = Path("src/gomazon_webasyst/contracts/applications.py")
PORT = Path(
    "src/gomazon_webasyst/application/ports/application_registry.py"
)


def test_application_registry_contracts_do_not_depend_on_outer_layers() -> None:
    forbidden = (
        "gomazon_webasyst.compatibility",
        "gomazon_webasyst.infrastructure",
        "gomazon_webasyst.presentation",
        "fastapi",
        "starlette",
        "sqlalchemy",
    )

    violations: list[str] = []
    for path in (CONTRACT, PORT):
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in source:
                violations.append(f"{path}:{token}")

    assert violations == []


def test_application_registry_contract_has_no_opaque_metadata_bag() -> None:
    source = CONTRACT.read_text(encoding="utf-8")
    assert "dict[str, Any]" not in source
    assert "dict[str, object]" not in source


def test_registry_port_has_no_nullable_or_boolean_lookup_results() -> None:
    source = PORT.read_text(encoding="utf-8")
    assert "Optional[" not in source
    assert "| None" not in source
    assert "-> bool" not in source


def test_api_execution_has_no_parallel_installed_app_store() -> None:
    assert not Path(
        "src/gomazon_webasyst/application/ports/installed_apps.py"
    ).exists()
    assert not Path(
        "src/gomazon_webasyst/infrastructure/api_execution/app_directory.py"
    ).exists()

    composition = Path(
        "src/gomazon_webasyst/composition/api_execution.py"
    ).read_text(encoding="utf-8")
    authorizer = Path(
        "src/gomazon_webasyst/application/api_execution/services/authorizer.py"
    ).read_text(encoding="utf-8")

    assert "InstalledAppDirectory" not in composition
    assert "InMemoryInstalledAppDirectory" not in composition
    assert "InstalledAppDirectory" not in authorizer
    assert "ApplicationRegistry" in authorizer


def test_dispatch_handler_registry_has_no_installation_state() -> None:
    assert not Path(
        "src/gomazon_webasyst/application/ports/dispatch_registry.py"
    ).exists()

    handler_port = Path(
        "src/gomazon_webasyst/application/ports/handler_registry.py"
    ).read_text(encoding="utf-8")
    handler_registry = Path(
        "src/gomazon_webasyst/compatibility/webasyst/dispatch/registry.py"
    ).read_text(encoding="utf-8")
    resolver = Path(
        "src/gomazon_webasyst/compatibility/webasyst/dispatch/resolver.py"
    ).read_text(encoding="utf-8")

    assert "plugin_available" not in handler_port
    assert "enable_plugin" not in handler_registry
    assert "_plugins" not in handler_registry
    assert "ApplicationRegistry" in resolver
    assert "PluginEnabled" in resolver
    assert "ApplicationEnabled" in resolver


def test_oauth_consent_catalog_is_registry_projection_only() -> None:
    assert not Path(
        "src/gomazon_webasyst/infrastructure/oauth_authorization/app_catalog.py"
    ).exists()

    projection = Path(
        "src/gomazon_webasyst/application/oauth_authorization/services/app_catalog.py"
    ).read_text(encoding="utf-8")
    composition = Path(
        "src/gomazon_webasyst/composition/oauth_authorization.py"
    ).read_text(encoding="utf-8")

    assert "ApplicationRegistry" in projection
    assert "ApplicationEnabled" in projection
    assert "InMemoryOAuthConsentAppCatalog" not in composition
    assert "RegistryBackedOAuthConsentAppCatalog" in composition
