from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from gomazon_webasyst.application.errors import ContactNotFound
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.contracts.contacts import ContactCreate, ContactRead, ContactUpdate
from gomazon_webasyst import main as main_module

NOW = datetime(2026, 9, 14, 12, 0, 0)


class FakeGetContact:
    async def execute(self, contact_id: int) -> ContactRead:
        if contact_id == 999:
            raise ContactNotFound(contact_id)
        return ContactRead(id=contact_id, name="Alice", create_datetime=NOW)


class FakeCreateContact:
    async def execute(self, data: ContactCreate) -> ContactRead:
        return ContactRead(id=1, create_datetime=NOW, **data.model_dump())


class FakeUpdateContact:
    async def execute(self, contact_id: int, data: ContactUpdate) -> ContactRead:
        values = ContactRead(id=contact_id, name="Alice", create_datetime=NOW).model_dump()
        values.update(data.model_dump(exclude_unset=True))
        return ContactRead(**values)


class FakeContainer:
    def __init__(self) -> None:
        self.get_contact = FakeGetContact()
        self.create_contact = FakeCreateContact()
        self.update_contact = FakeUpdateContact()
        self.api_execution = object()
        self.closed = 0

    async def close(self) -> None:
        self.closed += 1


@pytest.mark.asyncio
async def test_contact_http_routes_use_application_services(monkeypatch) -> None:
    container = FakeContainer()
    monkeypatch.setattr(main_module, "create_container", lambda settings: container)
    app = main_module.create_app_with_settings(Settings(database_url="sqlite+aiosqlite:///:memory:"))

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/v1/contacts",
                json={"name": "Alice", "firstname": "Alice"},
            )
            assert created.status_code == 201
            assert created.json()["id"] == 1

            loaded = await client.get("/api/v1/contacts/1")
            assert loaded.status_code == 200
            assert loaded.json()["name"] == "Alice"

            updated = await client.patch(
                "/api/v1/contacts/1",
                json={"company": "Example Ltd"},
            )
            assert updated.status_code == 200
            assert updated.json()["company"] == "Example Ltd"

            missing = await client.get("/api/v1/contacts/999")
            assert missing.status_code == 404
            assert missing.json() == {"detail": "contact 999 not found"}

            invalid = await client.post(
                "/api/v1/contacts",
                json={"name": "Alice", "email": "not-in-this-slice@example.com"},
            )
            assert invalid.status_code == 422

    assert container.closed == 1
