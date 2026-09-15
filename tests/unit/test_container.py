from types import SimpleNamespace

import pytest

from gomazon_webasyst.application.contacts import CreateContact, GetContact, UpdateContact
from gomazon_webasyst.composition import container as container_module
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
    monkeypatch.setattr(container_module, "create_engine", lambda settings: engine)
    monkeypatch.setattr(container_module, "create_uow_factory", lambda selected: uow_factory)
    monkeypatch.setattr(container_module, "create_session_factory", lambda selected: object())
    monkeypatch.setattr(
        container_module,
        "create_auth_use_cases",
        lambda selected: fake_auth_use_cases(),
    )

    container = container_module.create_container(
        Settings(database_url="mysql+asyncmy://user:pass@db/webasyst")
    )

    assert isinstance(container.get_contact, GetContact)
    assert isinstance(container.create_contact, CreateContact)
    assert isinstance(container.update_contact, UpdateContact)
    assert container.get_contact._uow_factory is uow_factory
    assert container.create_contact._uow_factory is uow_factory
    assert container.update_contact._uow_factory is uow_factory


@pytest.mark.asyncio
async def test_container_closes_persistence_resource(monkeypatch) -> None:
    engine = FakeEngine()
    monkeypatch.setattr(container_module, "create_engine", lambda settings: engine)
    monkeypatch.setattr(container_module, "create_uow_factory", lambda selected: object())
    monkeypatch.setattr(container_module, "create_session_factory", lambda selected: object())
    monkeypatch.setattr(
        container_module,
        "create_auth_use_cases",
        lambda selected: fake_auth_use_cases(),
    )
    container = container_module.create_container(
        Settings(database_url="sqlite+aiosqlite:///:memory:")
    )
    await container.close()
    assert engine.disposed == 1
