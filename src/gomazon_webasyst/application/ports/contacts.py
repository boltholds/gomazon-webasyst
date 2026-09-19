from typing import Protocol

from gomazon_webasyst.application.contact_deletion import (
    ContactDeletionApplied,
    ContactDeletionBatch,
)
from gomazon_webasyst.contracts.contacts import ContactCreate, ContactRead, ContactResolution, ContactUpdate


class ContactRepository(Protocol):
    async def get(self, contact_id: int) -> ContactResolution: ...

    async def create(self, data: ContactCreate) -> ContactRead: ...

    async def update(self, contact_id: int, data: ContactUpdate) -> ContactResolution: ...

    async def delete_batch(
        self,
        batch: ContactDeletionBatch,
    ) -> ContactDeletionApplied: ...
