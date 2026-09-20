from dataclasses import dataclass
from typing import Protocol

from gomazon_webasyst.application.contact_deletion import ContactDeletionBatch


@dataclass(slots=True, frozen=True)
class ContactsPrivateRightsDeleted:
    contact_ids: tuple[int, ...]


class ContactsPrivateRightsCleaner(Protocol):
    async def delete_for_contacts(
        self,
        batch: ContactDeletionBatch,
    ) -> ContactsPrivateRightsDeleted: ...
