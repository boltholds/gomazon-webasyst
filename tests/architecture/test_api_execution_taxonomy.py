from pathlib import Path

ROOT = Path("src/gomazon_webasyst/application/api_execution")


def test_api_execution_modules_are_classified_by_taxonomy() -> None:
    allowed = {"entities", "vo", "services", "composites"}
    for path in ROOT.rglob("*.py"):
        relative = path.relative_to(ROOT)
        if relative.name == "__init__.py":
            continue
        assert relative.parts[0] in allowed, path


def test_api_execution_application_has_no_framework_or_infrastructure_imports() -> None:
    forbidden = (
        "fastapi",
        "starlette",
        "sqlalchemy",
        "gomazon_webasyst.compatibility",
    )
    for path in ROOT.rglob("*.py"):
        source = path.read_text()
        for token in forbidden:
            assert token not in source, f"{token} leaked into {path}"
