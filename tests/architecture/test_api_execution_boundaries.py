from pathlib import Path

APPLICATION = Path("src/gomazon_webasyst/application/api_execution")
REGISTRY = Path("src/gomazon_webasyst/infrastructure/api_execution/method_registry.py")
HANDLER_PORT = Path("src/gomazon_webasyst/application/ports/api_methods.py")


def test_api_execution_application_dependency_boundaries() -> None:
    forbidden = (
        "fastapi",
        "starlette",
        "sqlalchemy",
        "gomazon_webasyst.compatibility",
        "wa_api_tokens",
        "wa_api_auth_codes",
        "importlib",
        "__import__",
    )
    for path in APPLICATION.rglob("*.py"):
        source = path.read_text()
        for token in forbidden:
            assert token not in source, f"{token} leaked into {path}"


def test_method_registry_does_not_build_classes_from_request_strings() -> None:
    source = REGISTRY.read_text()
    assert "importlib" not in source
    assert "__import__" not in source
    assert "class_name" not in source


def test_handler_port_accepts_typed_context_not_http_or_orm_objects() -> None:
    source = HANDLER_PORT.read_text()
    for forbidden in ("Request", "Response", "AsyncSession", "WaContactRow"):
        assert forbidden not in source


def test_taxonomy_has_no_unclassified_application_modules() -> None:
    allowed = {"entities", "vo", "services", "composites"}
    for path in APPLICATION.rglob("*.py"):
        relative = path.relative_to(APPLICATION)
        if relative.name == "__init__.py":
            continue
        assert relative.parts[0] in allowed
