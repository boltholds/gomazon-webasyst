from types import SimpleNamespace

import pytest

from gomazon_webasyst.application.contacts import CreateContact, GetContact, UpdateContact
from gomazon_webasyst.composition import container as container_module
from gomazon_webasyst.composition.session_state_providers import (
    SessionStateProviderRegistry,
    StateProviderName,
)
from gomazon_webasyst.composition.settings import Settings


class FakeEngine:
    def __init__(self) -> None:
        self.disposed = 0

    async def dispose(self) -> None:
        self.disposed += 1


def fake_auth_use_cases() -> SimpleNamespace:
    return SimpleNamespace(
        authenticate_backend_password=object(),
        resolve_backend_session=object(),
        logout_backend_session=object(),
        issue_persistent_credential=object(),
        restore_backend_session_from_persistent_credential=object(),
        revoke_persistent_credential=object(),
    )


def test_create_container_wires_all_contact_use_cases_to_one_uow_factory(monkeypatch) -> None:
    engine = FakeEngine()
    uow_factory = object()
    observed_session_state: list[object] = []
    monkeypatch.setattr(container_module, "create_engine", lambda settings: engine)
    monkeypatch.setattr(container_module, "create_uow_factory", lambda selected: uow_factory)
    monkeypatch.setattr(container_module, "create_session_factory", lambda selected: object())

    def fake_create_auth_use_cases(selected, *, session_state):
        observed_session_state.append(session_state)
        return fake_auth_use_cases()

    monkeypatch.setattr(container_module, "create_auth_use_cases", fake_create_auth_use_cases)

    container = container_module.create_container(
        Settings(database_url="mysql+asyncmy://user:pass@db/webasyst")
    )

    assert isinstance(container.get_contact, GetContact)
    assert isinstance(container.create_contact, CreateContact)
    assert isinstance(container.update_contact, UpdateContact)
    assert container.get_contact._uow_factory is uow_factory
    assert container.create_contact._uow_factory is uow_factory
    assert container.update_contact._uow_factory is uow_factory
    assert len(observed_session_state) == 1


@pytest.mark.asyncio
async def test_container_closes_persistence_resource(monkeypatch) -> None:
    engine = FakeEngine()
    monkeypatch.setattr(container_module, "create_engine", lambda settings: engine)
    monkeypatch.setattr(container_module, "create_uow_factory", lambda selected: object())
    monkeypatch.setattr(container_module, "create_session_factory", lambda selected: object())
    monkeypatch.setattr(
        container_module,
        "create_auth_use_cases",
        lambda selected, *, session_state: fake_auth_use_cases(),
    )
    container = container_module.create_container(
        Settings(database_url="sqlite+aiosqlite:///:memory:")
    )
    await container.close()
    assert engine.disposed == 1


def test_custom_session_state_registry_creates_one_store_and_passes_it_to_auth(monkeypatch) -> None:
    engine = FakeEngine()
    session_state = object()
    auth_states: list[object] = []

    class RecordingFactory:
        def __init__(self) -> None:
            self.calls = 0

        def create(self):
            self.calls += 1
            return session_state

    factory = RecordingFactory()
    registry = SessionStateProviderRegistry()
    registry.register(StateProviderName("custom"), factory)

    monkeypatch.setattr(container_module, "create_engine", lambda settings: engine)
    monkeypatch.setattr(container_module, "create_uow_factory", lambda selected: object())
    monkeypatch.setattr(container_module, "create_session_factory", lambda selected: object())

    def fake_create_auth_use_cases(selected, *, session_state):
        auth_states.append(session_state)
        return fake_auth_use_cases()

    monkeypatch.setattr(container_module, "create_auth_use_cases", fake_create_auth_use_cases)

    container = container_module.create_container_with_session_state_registry(
        Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            session_state_provider="custom",
        ),
        session_state_registry=registry,
    )

    assert container.settings.session_state_provider == "custom"
    assert factory.calls == 1
    assert auth_states == [session_state]
