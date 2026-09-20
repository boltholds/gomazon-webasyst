import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.contact_deletion import ContactDeletionBatch
from gomazon_webasyst.application.contacts_app.delete_rights import (
    DeleteContactsPrivateRights,
)
from gomazon_webasyst.application.contacts_app.ports import (
    ContactsPrivateRightsDeleted,
)
from gomazon_webasyst.application.events.vo.contacts import (
    ContactsDeleteEventPayload,
)
from gomazon_webasyst.application.events.vo.identity import (
    EventHandlerId,
    EventKey,
    EventName,
)
from gomazon_webasyst.application.events.vo.payload import (
    EventHandlerNoResult,
    LegacyEventPayload,
)
from gomazon_webasyst.application.ports.event_handlers import EventHandlerContext
from gomazon_webasyst.compatibility.webasyst.contacts.events import (
    ContactsDeletePrivateRightsHandler,
)


class RecordingCleaner:
    def __init__(self) -> None:
        self.batches: list[ContactDeletionBatch] = []

    async def delete_for_contacts(
        self,
        batch: ContactDeletionBatch,
    ) -> ContactsPrivateRightsDeleted:
        self.batches.append(batch)
        return ContactsPrivateRightsDeleted(contact_ids=batch.contact_ids)


def _context() -> EventHandlerContext:
    return EventHandlerContext(
        event=EventKey(AppId("contacts"), EventName("delete")),
        handler_id=EventHandlerId("contacts-private-rights-delete"),
    )


@pytest.mark.asyncio
async def test_contacts_delete_handler_delegates_positive_contact_ids() -> None:
    cleaner = RecordingCleaner()
    handler = ContactsDeletePrivateRightsHandler(
        DeleteContactsPrivateRights(cleaner)
    )

    outcome = await handler.handle(
        _context(),
        ContactsDeleteEventPayload(contact_ids=(7, 8, 7)),
    )

    assert isinstance(outcome, EventHandlerNoResult)
    assert cleaner.batches == [
        ContactDeletionBatch(contact_ids=(7, 8, 7))
    ]


@pytest.mark.asyncio
async def test_contacts_delete_handler_rejects_wrong_payload_shape() -> None:
    cleaner = RecordingCleaner()
    handler = ContactsDeletePrivateRightsHandler(
        DeleteContactsPrivateRights(cleaner)
    )

    with pytest.raises(TypeError, match="ContactsDeleteEventPayload"):
        await handler.handle(_context(), LegacyEventPayload(value={"id": 7}))

    assert cleaner.batches == []
