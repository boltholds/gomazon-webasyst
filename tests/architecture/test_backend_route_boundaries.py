import ast
from pathlib import Path


ROOT = Path("src/gomazon_webasyst/compatibility/webasyst/routing")


def test_backend_route_loading_has_no_php_execution_or_dynamic_imports() -> None:
    forbidden_calls = {"eval", "exec", "__import__"}
    forbidden_modules = {"subprocess", "importlib"}
    violations: list[str] = []

    for path in ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in forbidden_calls:
                    violations.append(f"{path}:{node.lineno}:{node.func.id}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".", 1)[0] in forbidden_modules:
                        violations.append(f"{path}:{node.lineno}:{alias.name}")
            if isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".", 1)[0]
                if module in forbidden_modules:
                    violations.append(f"{path}:{node.lineno}:{node.module}")

    assert violations == []
