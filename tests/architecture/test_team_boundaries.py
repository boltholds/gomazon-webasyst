import ast
from pathlib import Path


APPLICATION = Path("src/gomazon_webasyst/application/team")
COMPOSITION = Path("src/gomazon_webasyst/composition/team.py")


def test_team_application_does_not_import_transport_orm_compatibility_or_infrastructure() -> None:
    forbidden = (
        "fastapi",
        "starlette",
        "sqlalchemy",
        "gomazon_webasyst.compatibility",
        "gomazon_webasyst.infrastructure",
    )
    violations: list[str] = []
    for path in APPLICATION.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
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
                    violations.append(f"{path}:{node.lineno}:{name}")
    assert violations == []


def test_team_runtime_registration_is_explicit_not_dynamic() -> None:
    source = COMPOSITION.read_text(encoding="utf-8")
    assert 'ApiMethodName("groups.getList")' in source
    assert 'AppId("team")' in source
    for forbidden in ("importlib", "__import__", "eval(", "exec(", "pkgutil"):
        assert forbidden not in source
