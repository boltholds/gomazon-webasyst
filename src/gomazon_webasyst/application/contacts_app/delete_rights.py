from gomazon_webasyst.application.contact_deletion import ContactDeletionBatch
from gomazon_webasyst.application.contacts_app.ports import (
    ContactsPrivateRightsCleaner,
    ContactsPrivateRightsDeleted,
)


class DeleteContactsPrivateRights:
    def __init__(self, cleaner: ContactsPrivateRightsCleaner) -> None:
        self._cleaner = cleaner

    async def execute(
        self,
        batch: ContactDeletionBatch,
    ) -> ContactsPrivateRightsDeleted:
        return await self._cleaner.delete_for_contacts(batch)
