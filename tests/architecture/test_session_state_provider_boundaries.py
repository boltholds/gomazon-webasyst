from pathlib import Path


SOURCE_ROOT = Path("src/gomazon_webasyst")


def test_auth_composition_does_not_select_concrete_session_backend() -> None:
    source = (SOURCE_ROOT / "composition" / "auth.py").read_text()

    assert "InMemorySessionStateStore" not in source
    assert "infrastructure.sessions.memory" not in source


def test_application_does_not_import_session_provider_registry() -> None:
    for path in (SOURCE_ROOT / "application").rglob("*.py"):
        source = path.read_text()
        assert "composition.session_state_providers" not in source, path


def test_container_selects_session_state_through_registry_not_named_backend_branches() -> None:
    source = (SOURCE_ROOT / "composition" / "container.py").read_text()

    assert "resolve_session_state_store" in source
    assert "create_default_session_state_provider_registry" in source
    assert "InMemorySessionStateStore" not in source
    assert '"redis"' not in source
    assert '"supabase"' not in source
