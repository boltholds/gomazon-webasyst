import ast
from pathlib import Path


SRC = Path("src/gomazon_webasyst")
RUNTIME_ROOTS = (
    SRC / "application" / "runtime",
    SRC / "application" / "events",
    SRC / "application" / "plugins",
    SRC / "compatibility" / "webasyst" / "plugins",
    SRC / "compatibility" / "webasyst" / "events",
    SRC / "infrastructure" / "plugins",
    SRC / "infrastructure" / "events",
)
PRESENTATION = SRC / "presentation"
COMPOSITION = SRC / "composition"


def _sources(root: Path):
    return [
        (path, path.read_text(encoding="utf-8"))
        for path in root.rglob("*.py")
    ]


def test_runtime_plugin_event_source_has_no_execution_or_dynamic_import_primitives() -> None:
    forbidden_calls = {"eval", "exec", "__import__"}
    forbidden_import_roots = {"subprocess", "importlib"}
    violations: list[str] = []

    for root in RUNTIME_ROOTS:
        for path, source in _sources(root):
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id in forbidden_calls:
                        violations.append(
                            f"{path}:{node.lineno}:{node.func.id}"
                        )
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if (
                            alias.name.split(".", 1)[0]
                            in forbidden_import_roots
                        ):
                            violations.append(
                                f"{path}:{node.lineno}:{alias.name}"
                            )
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if module.split(".", 1)[0] in forbidden_import_roots:
                        violations.append(
                            f"{path}:{node.lineno}:{module}"
                        )

    assert violations == []


def test_installed_metadata_entities_do_not_contain_executable_callables() -> None:
    files = (
        SRC
        / "application"
        / "application_registry"
        / "entities"
        / "installed_application.py",
        SRC
        / "application"
        / "plugins"
        / "entities"
        / "installed_plugin.py",
    )
    forbidden = (
        "Callable",
        "Protocol",
        "handler:",
        "handler =",
        "execute",
        "service",
        "repository",
    )
    violations: list[str] = []
    for path in files:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in source:
                violations.append(f"{path}:{token}")
    assert violations == []


def test_application_runtime_package_has_no_filesystem_discovery_dependency() -> None:
    root = SRC / "application" / "runtime"
    forbidden = (
        "pathlib",
        "FilesystemInstalled",
        "compatibility.webasyst",
        "infrastructure.plugins",
    )
    violations: list[str] = []
    for path, source in _sources(root):
        for token in forbidden:
            if token in source:
                violations.append(f"{path}:{token}")
    assert violations == []


def test_presentation_cannot_mutate_startup_runtime_registries_or_discover_filesystem() -> None:
    forbidden = (
        "DispatchRegistrationSink",
        "EventHandlerRegistry",
        "ApiMethodRegistry",
        "ApplicationRuntimeLinker",
        "FilesystemInstalledPluginCatalog",
        "FilesystemInstalledApplicationCatalog",
        ".register(",
    )
    violations: list[str] = []
    for path, source in _sources(PRESENTATION):
        for token in forbidden:
            if token in source:
                violations.append(f"{path}:{token}")
    assert violations == []


def test_api_dispatch_event_registries_remain_distinct_contracts() -> None:
    api = (
        SRC / "application" / "ports" / "api_method_registry.py"
    ).read_text(encoding="utf-8")
    dispatch = (
        SRC / "application" / "ports" / "dispatch_registry.py"
    ).read_text(encoding="utf-8")
    events = (
        SRC / "application" / "ports" / "event_handlers.py"
    ).read_text(encoding="utf-8")

    assert "class ApiMethodRegistry" in api
    assert "class DispatchRegistry" in dispatch
    assert "class EventHandlerRegistry" in events
    assert "DispatchRegistry" not in api
    assert "EventHandlerRegistry" not in api
    assert "ApiMethodRegistry" not in dispatch
    assert "EventHandlerRegistry" not in dispatch


def test_runtime_linker_is_invoked_only_from_application_runtime_composition() -> None:
    allowed = COMPOSITION / "application_runtime.py"
    violations: list[str] = []
    for path, source in _sources(COMPOSITION):
        if "ApplicationRuntimeLinker(" in source and path != allowed:
            violations.append(str(path))
    assert violations == []
    assert "ApplicationRuntimeLinker(" in allowed.read_text(encoding="utf-8")


def test_request_time_http_code_does_not_import_legacy_plugin_discovery() -> None:
    forbidden = (
        "compatibility.webasyst.plugins",
        "infrastructure.plugins.filesystem_catalog",
    )
    violations: list[str] = []
    for path, source in _sources(PRESENTATION):
        for token in forbidden:
            if token in source:
                violations.append(f"{path}:{token}")
    assert violations == []
