import ast
from pathlib import Path


SRC = Path("src/gomazon_webasyst")
APPLICATION_REGISTRY = SRC / "application" / "application_registry"
COMPAT_REGISTRY = SRC / "compatibility" / "webasyst" / "application_registry"
COMPOSITION = SRC / "composition"
OLD_PORT = SRC / "application" / "ports" / "installed_apps.py"
OLD_DIRECTORY = SRC / "infrastructure" / "api_execution" / "app_directory.py"
API_METHOD_REGISTRY = SRC / "application" / "ports" / "api_method_registry.py"
DISPATCH_REGISTRY = SRC / "application" / "ports" / "dispatch_registry.py"


def _python_sources(root: Path) -> list[tuple[Path, str]]:
    return [
        (path, path.read_text(encoding="utf-8"))
        for path in root.rglob("*.py")
    ]


def test_obsolete_installed_app_directory_files_are_removed() -> None:
    assert not OLD_PORT.exists()
    assert not OLD_DIRECTORY.exists()


def test_production_composition_does_not_construct_independent_empty_app_universes() -> None:
    forbidden = (
        "InMemoryInstalledApplicationCatalog(())",
        "InMemoryInstalledAppDirectory",
        "InMemoryOAuthConsentAppCatalog(())",
    )
    violations: list[str] = []
    for path, source in _python_sources(COMPOSITION):
        for token in forbidden:
            if token in source:
                violations.append(f"{path}:{token}")
    assert violations == []


def test_application_registry_parser_cannot_execute_php_or_dynamic_imports() -> None:
    forbidden_names = {
        "eval",
        "exec",
        "__import__",
    }
    forbidden_import_roots = {
        "subprocess",
        "importlib",
    }
    violations: list[str] = []
    for path in COMPAT_REGISTRY.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in forbidden_names:
                    violations.append(f"{path}:{node.lineno}:{node.func.id}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".", 1)[0] in forbidden_import_roots:
                        violations.append(f"{path}:{node.lineno}:{alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.split(".", 1)[0] in forbidden_import_roots:
                    violations.append(f"{path}:{node.lineno}:{module}")
    assert violations == []


def test_application_layer_does_not_import_legacy_registry_parser_or_filesystem_catalog() -> None:
    forbidden = (
        "compatibility.webasyst.application_registry",
        "infrastructure.application_registry.filesystem_catalog",
        "pathlib",
    )
    violations: list[str] = []
    for path, source in _python_sources(APPLICATION_REGISTRY):
        for token in forbidden:
            if token in source:
                violations.append(f"{path}:{token}")
    assert violations == []


def test_api_method_and_dispatch_registries_remain_separate_from_app_catalog() -> None:
    assert API_METHOD_REGISTRY.exists()
    assert DISPATCH_REGISTRY.exists()
    api_source = API_METHOD_REGISTRY.read_text(encoding="utf-8")
    dispatch_source = DISPATCH_REGISTRY.read_text(encoding="utf-8")
    assert "InstalledApplicationCatalog" not in api_source
    assert "InstalledApplicationCatalog" not in dispatch_source


def test_container_has_one_canonical_catalog_field_and_factory_path() -> None:
    source = (COMPOSITION / "container.py").read_text(encoding="utf-8")
    assert "installed_application_catalog: InstalledApplicationCatalog" in source
    assert source.count("create_installed_application_catalog(settings)") == 2
    assert "create_container_with_application_catalog" in source
    assert "create_container_with_registries" in source
