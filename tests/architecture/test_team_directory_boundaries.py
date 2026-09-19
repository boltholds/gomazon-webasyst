import ast
from pathlib import Path


SRC = Path("src/gomazon_webasyst")
TEAM_APP = SRC / "application" / "team_directory"
TEAM_INFRA = SRC / "infrastructure" / "team_directory"
TEAM_COMPAT = SRC / "compatibility" / "webasyst" / "team"
TEAM_COMPOSITION = SRC / "composition" / "team_directory.py"


def _sources(root: Path):
    if root.is_file():
        return [(root, root.read_text(encoding="utf-8"))]
    return [
        (path, path.read_text(encoding="utf-8"))
        for path in root.rglob("*.py")
    ]


def test_team_application_layer_has_no_transport_orm_compatibility_or_infrastructure_dependencies() -> None:
    forbidden = (
        "fastapi",
        "starlette",
        "sqlalchemy",
        "gomazon_webasyst.compatibility",
        "gomazon_webasyst.infrastructure",
    )
    violations: list[str] = []
    for path, source in _sources(TEAM_APP):
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if any(
                    name == prefix
                    or name.startswith(prefix + ".")
                    for prefix in forbidden
                ):
                    violations.append(
                        f"{path}:{node.lineno}:{name}"
                    )
    assert violations == []


def test_team_sqlalchemy_types_remain_in_infrastructure() -> None:
    assert TEAM_INFRA.exists()
    for path, source in _sources(TEAM_APP):
        assert "sqlalchemy" not in source
    for path, source in _sources(TEAM_COMPAT):
        assert "sqlalchemy" not in source


def test_team_api_targets_are_registered_only_by_team_composition() -> None:
    target_tokens = (
        'ApiMethodName("users.getList")',
        'ApiMethodName("groups.getList")',
    )
    allowed = TEAM_COMPOSITION
    violations: list[str] = []
    for path, source in _sources(SRC):
        for token in target_tokens:
            if token in source and path != allowed:
                violations.append(f"{path}:{token}")
    assert violations == []


def test_team_slice_does_not_introduce_backend_rendering_or_route_loading() -> None:
    forbidden = (
        "routing.backend.php",
        "smarty",
        "jinja",
        "legacy_dispatch",
        "create_legacy_compatibility_router",
    )
    violations: list[str] = []
    for root in (TEAM_APP, TEAM_INFRA, TEAM_COMPAT, TEAM_COMPOSITION):
        for path, source in _sources(root):
            lowered = source.lower()
            for token in forbidden:
                if token.lower() in lowered:
                    violations.append(f"{path}:{token}")
    assert violations == []


def test_team_slice_has_no_dynamic_code_loading_or_php_execution() -> None:
    forbidden_calls = {"eval", "exec", "__import__"}
    forbidden_imports = {"subprocess", "importlib"}
    violations: list[str] = []
    for root in (TEAM_APP, TEAM_INFRA, TEAM_COMPAT, TEAM_COMPOSITION):
        for path, source in _sources(root):
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id in forbidden_calls
                ):
                    violations.append(
                        f"{path}:{node.lineno}:{node.func.id}"
                    )
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if (
                            alias.name.split(".", 1)[0]
                            in forbidden_imports
                        ):
                            violations.append(
                                f"{path}:{node.lineno}:{alias.name}"
                            )
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if module.split(".", 1)[0] in forbidden_imports:
                        violations.append(
                            f"{path}:{node.lineno}:{module}"
                        )
    assert violations == []


def test_production_container_uses_team_runtime_factory_builder() -> None:
    source = (
        SRC / "composition" / "container.py"
    ).read_text(encoding="utf-8")
    assert "TeamRuntimeModuleFactoryBuilder(settings)" in source
    assert "create_default_application_runtime_modules" not in source
