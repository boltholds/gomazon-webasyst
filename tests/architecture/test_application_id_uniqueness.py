import ast
from pathlib import Path


APPLICATION_ROOT = Path("src/gomazon_webasyst/application")
CANONICAL_APP_VALUES = APPLICATION_ROOT / "app_values.py"


def test_application_layer_has_one_concrete_app_id_definition() -> None:
    definitions: list[Path] = []
    for path in APPLICATION_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if any(
            isinstance(node, ast.ClassDef) and node.name == "AppId"
            for node in ast.walk(tree)
        ):
            definitions.append(path)

    assert definitions == [CANONICAL_APP_VALUES]
