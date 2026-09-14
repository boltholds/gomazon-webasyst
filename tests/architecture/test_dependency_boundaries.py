import ast
from pathlib import Path

ROOT = Path("src/gomazon_webasyst")
CHECK_DIRS = [ROOT / "contracts", ROOT / "application"]
FORBIDDEN = {"fastapi", "sqlalchemy", "asyncmy", "aiosqlite", "hashlib"}


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def test_application_and_contracts_do_not_import_framework_or_db_internals() -> None:
    violations: list[str] = []
    for directory in CHECK_DIRS:
        if not directory.exists():
            continue
        for path in directory.rglob("*.py"):
            bad = imported_roots(path) & FORBIDDEN
            if bad:
                violations.append(f"{path}: {sorted(bad)}")
    assert violations == []
