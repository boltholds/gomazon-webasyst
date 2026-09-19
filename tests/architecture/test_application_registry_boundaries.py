from pathlib import Path


CONTRACT = Path("src/gomazon_webasyst/contracts/applications.py")
PORT = Path(
    "src/gomazon_webasyst/application/ports/application_registry.py"
)


def test_application_registry_contracts_do_not_depend_on_outer_layers() -> None:
    forbidden = (
        "gomazon_webasyst.compatibility",
        "gomazon_webasyst.infrastructure",
        "gomazon_webasyst.presentation",
        "fastapi",
        "starlette",
        "sqlalchemy",
    )

    violations: list[str] = []
    for path in (CONTRACT, PORT):
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in source:
                violations.append(f"{path}:{token}")

    assert violations == []


def test_application_registry_contract_has_no_opaque_metadata_bag() -> None:
    source = CONTRACT.read_text(encoding="utf-8")
    assert "dict[str, Any]" not in source
    assert "dict[str, object]" not in source


def test_registry_port_has_no_nullable_or_boolean_lookup_results() -> None:
    source = PORT.read_text(encoding="utf-8")
    assert "Optional[" not in source
    assert "| None" not in source
    assert "-> bool" not in source
