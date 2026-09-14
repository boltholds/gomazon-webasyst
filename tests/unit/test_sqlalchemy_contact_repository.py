from datetime import datetime

import pytest

from gomazon_webasyst.contracts.contacts import ContactCreate, ContactUpdate
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import WaContactRow
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.repositories import SQLAlchemyContactRepository


class FakeAsyncSession:
    def __init__(self) -> None:
        self.rows: dict[int, WaContactRow] = {}
        self.next_id = 1
        self.flushed = 0

    async def get(self, model, row_id: int):
        assert model is WaContactRow
        return self.rows.get(row_id)

    def add(self, row: WaContactRow) -> None:
        if row.id is None:
            row.id = self.next_id
            self.next_id += 1
        self.rows[row.id] = row

    async def flush(self) -> None:
        self.flushed += 1


@pytest.mark.asyncio
async def test_repository_create_returns_pydantic_contract() -> None:
    session = FakeAsyncSession()
    repo = SQLAlchemyContactRepository(session)  # type: ignore[arg-type]
    created = await repo.create(ContactCreate(name="Alice", is_company=True))
    assert created.id == 1
    assert created.name == "Alice"
    assert created.is_company is True
    assert session.rows[1].is_company == 1
    assert isinstance(created.create_datetime, datetime)
    assert session.flushed == 1


@pytest.mark.asyncio
async def test_repository_get_and_update() -> None:
    session = FakeAsyncSession()
    repo = SQLAlchemyContactRepository(session)  # type: ignore[arg-type]
    created = await repo.create(ContactCreate(name="Alice"))
    assert await repo.get(created.id) == created

    updated = await repo.update(created.id, ContactUpdate(company="Example Ltd"))
    assert updated is not None
    assert updated.company == "Example Ltd"
    assert session.rows[created.id].company == "Example Ltd"


@pytest.mark.asyncio
async def test_repository_missing_rows_return_none() -> None:
    repo = SQLAlchemyContactRepository(FakeAsyncSession())  # type: ignore[arg-type]
    assert await repo.get(123) is None
    assert await repo.update(123, ContactUpdate(name="Nobody")) is None
