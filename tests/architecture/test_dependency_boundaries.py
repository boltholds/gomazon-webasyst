import ast
from pathlib import Path

ROOT = Path("src/gomazon_webasyst")
CHECK_DIRS = [ROOT / "contracts", ROOT / "application"]
FORBIDDEN = {"fastapi", "sqlalchemy", "asyncmy", "aiosqlite", "hashlib"}
PERSISTENT_APPLICATION_FILES = (
    ROOT / "application" / "persistent_login.py",
    ROOT / "application" / "session_establishment.py",
    ROOT / "application" / "ports" / "persistent_credentials.py",
)
PERSISTENT_FORBIDDEN_PREFIXES = (
    "fastapi",
    "starlette",
    "sqlalchemy",
    "hashlib",
    "http.cookies",
    "gomazon_webasyst.compatibility",
)
ACL_APPLICATION_FILES = (
    ROOT / "application" / "access_control.py",
    ROOT / "application" / "access_admin_policy.py",
    ROOT / "application" / "access_values.py",
    ROOT / "application" / "rights_evaluator.py",
    ROOT / "application" / "rights_mutation_policy.py",
    ROOT / "application" / "ports" / "access_admin_policy.py",
    ROOT / "application" / "ports" / "access_control_uow.py",
    ROOT / "application" / "ports" / "access_semantics.py",
    ROOT / "application" / "ports" / "access_subjects.py",
    ROOT / "application" / "ports" / "groups.py",
    ROOT / "application" / "ports" / "memberships.py",
    ROOT / "application" / "ports" / "rights.py",
)
ACL_FORBIDDEN_PREFIXES = (
    "fastapi",
    "starlette",
    "sqlalchemy",
    "gomazon_webasyst.compatibility",
)
ACL_FORBIDDEN_STORAGE_LITERALS = {
    "backend",
    "webasyst",
    "wa_contact_rights",
}


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def string_literals(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


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


def test_persistent_login_application_does_not_import_transport_db_or_legacy_codec() -> None:
    violations: list[str] = []
    for path in PERSISTENT_APPLICATION_FILES:
        modules = imported_modules(path)
        bad = sorted(
            module
            for module in modules
            if module.startswith(PERSISTENT_FORBIDDEN_PREFIXES)
        )
        if bad:
            violations.append(f"{path}: {bad}")
    assert violations == []


def test_access_control_application_does_not_import_db_or_webasyst_compatibility() -> None:
    violations: list[str] = []
    for path in ACL_APPLICATION_FILES:
        modules = imported_modules(path)
        bad = sorted(
            module
            for module in modules
            if module.startswith(ACL_FORBIDDEN_PREFIXES)
        )
        if bad:
            violations.append(f"{path}: {bad}")
    assert violations == []


def test_access_control_application_does_not_encode_legacy_storage_principals_or_backend_keys() -> None:
    violations: list[str] = []
    for path in ACL_APPLICATION_FILES:
        text = path.read_text(encoding="utf-8")
        literals = string_literals(path) & ACL_FORBIDDEN_STORAGE_LITERALS
        if literals:
            violations.append(f"{path}: forbidden literals {sorted(literals)}")
        if "LegacyPrincipalId" in text:
            violations.append(f"{path}: LegacyPrincipalId")
    assert violations == []
