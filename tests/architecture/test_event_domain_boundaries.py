import ast
from pathlib import Path


ROOT = Path("src/gomazon_webasyst/application/events")
ALLOWED = {"entities", "vo", "services", "composites"}


def test_event_application_modules_are_taxonomy_classified() -> None:
    violations: list[str] = []
    for path in ROOT.rglob("*.py"):
        relative = path.relative_to(ROOT)
        if relative.name == "__init__.py":
            continue
        if not relative.parts or relative.parts[0] not in ALLOWED:
            violations.append(str(path))
    assert violations == []


def test_event_application_has_no_transport_orm_compatibility_or_dynamic_loading_dependencies() -> None:
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


def test_event_application_contracts_do_not_encode_wildcard_as_literal_star() -> None:
    violations: list[str] = []
    for path in ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        if '"*"' in source or "'*'" in source:
            violations.append(str(path))
    assert violations == []
