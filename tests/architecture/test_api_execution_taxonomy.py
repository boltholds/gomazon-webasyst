import ast
from pathlib import Path


ROOT = Path("src/gomazon_webasyst/application/api_execution")
ALLOWED = {"entities", "vo", "services", "composites"}


def test_api_execution_application_modules_are_taxonomy_classified() -> None:
    violations: list[str] = []
    if not ROOT.exists():
        raise AssertionError("api_execution package is missing")
    for path in ROOT.rglob("*.py"):
        relative = path.relative_to(ROOT)
        if relative.name == "__init__.py":
            continue
        if not relative.parts or relative.parts[0] not in ALLOWED:
            violations.append(str(path))
    assert violations == []


def test_api_execution_application_has_no_forbidden_dependencies() -> None:
    forbidden = (
        "fastapi",
        "starlette",
        "sqlalchemy",
        "gomazon_webasyst.compatibility",
    )
    violations: list[str] = []
    if not ROOT.exists():
        raise AssertionError("api_execution package is missing")
    for path in ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            module = ""
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
