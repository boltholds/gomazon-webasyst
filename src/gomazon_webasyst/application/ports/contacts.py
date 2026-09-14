from typing import Protocol

from gomazon_webasyst.contracts.contacts import ContactCreate, ContactRead, ContactUpdate


class ContactRepository(Protocol):
    async def get(self, contact_id: int) -> ContactRead | None: ...

    async def create(self, data: ContactCreate) -> ContactRead: ...

    async def update(self, contact_id: int, data: ContactUpdate) -> ContactRead | None: ...
