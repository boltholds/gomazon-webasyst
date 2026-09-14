from datetime import datetime

import pytest

from gomazon_webasyst.application.contacts import CreateContact, GetContact, UpdateContact
from gomazon_webasyst.application.errors import ContactNotFound
from gomazon_webasyst.contracts.contacts import ContactCreate, ContactMissing, ContactRead, ContactResolved, ContactResolution, ContactUpdate

NOW = datetime(2026, 9, 14, 12, 0, 0)


class FakeRepo:
    def __init__(self) -> None:
        self.items: dict[int, ContactRead] = {}
        self.next_id = 1

    async def get(self, contact_id: int) -> ContactResolution:
        if contact_id not in self.items:
            return ContactMissing(contact_id=contact_id)
        return ContactResolved(contact=self.items[contact_id])

    async def create(self, data: ContactCreate) -> ContactRead:
        item = ContactRead(id=self.next_id, create_datetime=NOW, **data.model_dump())
        self.items[item.id] = item
        self.next_id += 1
        return item

    async def update(self, contact_id: int, data: ContactUpdate) -> ContactResolution:
        if contact_id not in self.items:
            return ContactMissing(contact_id=contact_id)
        current = self.items[contact_id]
        values = current.model_dump()
        values.update(data.model_dump(exclude_unset=True))
        item = ContactRead(**values)
        self.items[contact_id] = item
        return ContactResolved(contact=item)


class FakeUow:
    def __init__(self, repo: FakeRepo) -> None:
        self.contacts = repo
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeUowFactory:
    def __init__(self, uow: FakeUow) -> None:
        self.uow = uow

    def __call__(self) -> FakeUow:
        return self.uow


@pytest.mark.asyncio
async def test_create_commits() -> None:
    uow = FakeUow(FakeRepo())
    result = await CreateContact(FakeUowFactory(uow)).execute(ContactCreate(name="Alice"))
    assert result.id == 1
    assert uow.commits == 1


@pytest.mark.asyncio
async def test_get_missing_raises_typed_error() -> None:
    uow = FakeUow(FakeRepo())
    with pytest.raises(ContactNotFound):
        await GetContact(FakeUowFactory(uow)).execute(99)


@pytest.mark.asyncio
async def test_update_commits() -> None:
    repo = FakeRepo()
    existing = await repo.create(ContactCreate(name="Before"))
    uow = FakeUow(repo)
    result = await UpdateContact(FakeUowFactory(uow)).execute(
        existing.id,
        ContactUpdate(name="After"),
    )
    assert result.name == "After"
    assert uow.commits == 1
