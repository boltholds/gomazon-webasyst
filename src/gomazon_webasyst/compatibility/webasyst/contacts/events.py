from gomazon_webasyst.application.contact_deletion import ContactDeletionBatch
from gomazon_webasyst.application.contacts_app.delete_rights import (
    DeleteContactsPrivateRights,
)
from gomazon_webasyst.application.events.vo.contacts import (
    ContactsDeleteEventPayload,
)
from gomazon_webasyst.application.events.vo.payload import (
    EventHandlerNoResult,
    EventPayload,
)
from gomazon_webasyst.application.ports.event_handlers import EventHandlerContext


class ContactsDeletePrivateRightsHandler:
    def __init__(self, delete_rights: DeleteContactsPrivateRights) -> None:
        self._delete_rights = delete_rights

    async def handle(
        self,
        context: EventHandlerContext,
        payload: EventPayload,
    ) -> EventHandlerNoResult:
        del context
        if not isinstance(payload, ContactsDeleteEventPayload):
            raise TypeError(
                "contacts.delete private-rights handler requires "
                "ContactsDeleteEventPayload"
            )
        await self._delete_rights.execute(
            ContactDeletionBatch(contact_ids=payload.contact_ids)
        )
        return EventHandlerNoResult()
