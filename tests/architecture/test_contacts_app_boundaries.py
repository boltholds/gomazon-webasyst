import ast
from pathlib import Path


APPLICATION = Path("src/gomazon_webasyst/application/contacts_app")
COMPOSITION = Path("src/gomazon_webasyst/composition/contacts.py")
CORE_REPOSITORY = Path(
    "src/gomazon_webasyst/infrastructure/persistence/sqlalchemy/repositories.py"
)


def test_contacts_app_application_has_clean_dependency_direction() -> None:
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


def test_contacts_runtime_registration_is_explicit() -> None:
    source = COMPOSITION.read_text(encoding="utf-8")
    assert 'AppId("contacts")' in source
    assert 'EventName("delete")' in source
    assert "ContactsDeletePrivateRightsHandler" in source
    for forbidden in ("importlib", "__import__", "eval(", "exec(", "pkgutil"):
        assert forbidden not in source


def test_core_contact_repository_does_not_own_contacts_private_rights() -> None:
    source = CORE_REPOSITORY.read_text(encoding="utf-8")
    assert '"contacts_rights"' not in source
