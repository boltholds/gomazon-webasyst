import ast
from pathlib import Path


ROOT = Path("src/gomazon_webasyst/application/plugins")
ALLOWED = {"entities", "vo", "services", "composites"}


def test_plugin_domain_modules_are_taxonomy_classified() -> None:
    violations: list[str] = []
    for path in ROOT.rglob("*.py"):
        relative = path.relative_to(ROOT)
        if relative.name == "__init__.py":
            continue
        if not relative.parts or relative.parts[0] not in ALLOWED:
            violations.append(str(path))
    assert violations == []


def test_plugin_domain_has_no_transport_orm_filesystem_or_dynamic_loading_dependencies() -> None:
    forbidden = (
        "fastapi",
        "starlette",
        "sqlalchemy",
        "pathlib",
        "subprocess",
        "importlib",
        "gomazon_webasyst.compatibility",
        "gomazon_webasyst.infrastructure",
    )
    violations: list[str] = []
    for path in ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden):
                    violations.append(f"{path}:{node.lineno}:{name}")
    assert violations == []


def test_installed_plugin_entity_contains_no_callable_or_runtime_handler_field() -> None:
    source = (ROOT / "entities" / "installed_plugin.py").read_text(encoding="utf-8")
    forbidden = ("Callable", "Protocol", "handler:", "service", "repository")
    for token in forbidden:
        assert token not in source
