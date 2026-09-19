import ast
from pathlib import Path


TEAM_EVENTS = Path(
    "src/gomazon_webasyst/compatibility/webasyst/team/events.py"
)
PUBLISHER_PORT = Path(
    "src/gomazon_webasyst/application/ports/event_publisher.py"
)
RUNTIME_COMPOSITION = Path(
    "src/gomazon_webasyst/composition/application_runtime.py"
)


def test_team_nested_event_handler_depends_on_publisher_port_not_concrete_dispatcher() -> None:
    source = TEAM_EVENTS.read_text(encoding="utf-8")
    assert "application.ports.event_publisher" in source
    assert "EventPublisher" in source
    assert "EventDispatcher" not in source
    assert "InMemoryEventHandlerRegistry" not in source


def test_event_publisher_port_has_no_compatibility_infrastructure_or_composition_dependency() -> None:
    tree = ast.parse(PUBLISHER_PORT.read_text(encoding="utf-8"))
    forbidden = (
        "gomazon_webasyst.compatibility",
        "gomazon_webasyst.infrastructure",
        "gomazon_webasyst.composition",
        "fastapi",
        "starlette",
        "sqlalchemy",
    )
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        for name in names:
            if any(
                name == prefix or name.startswith(prefix + ".")
                for prefix in forbidden
            ):
                violations.append(f"{node.lineno}:{name}")
    assert violations == []


def test_known_runtime_factory_selection_uses_no_package_scanning_or_dynamic_imports() -> None:
    source = RUNTIME_COMPOSITION.read_text(encoding="utf-8")
    for forbidden in (
        "importlib",
        "pkgutil",
        "__import__",
        "eval(",
        "exec(",
    ):
        assert forbidden not in source
    assert "KnownRuntimeModuleFactory" in source
    assert "InstalledKnownRuntimeModuleFactories" in source
