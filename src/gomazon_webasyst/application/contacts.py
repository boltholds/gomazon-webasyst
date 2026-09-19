from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.contact_deletion import (
    ContactDeletionApplied,
    ContactDeletionBatch,
)
from gomazon_webasyst.application.errors import ContactNotFound
from gomazon_webasyst.application.events.composites.contracts import (
    EventDispatchRequest,
)
from gomazon_webasyst.application.events.vo.contacts import (
    ContactsDeleteEventPayload,
)
from gomazon_webasyst.application.events.vo.identity import EventKey, EventName
from gomazon_webasyst.application.ports.event_publisher import EventPublisher
from gomazon_webasyst.application.ports.unit_of_work import UnitOfWorkFactory
from gomazon_webasyst.contracts.contacts import ContactCreate, ContactMissing, ContactRead, ContactResolved, ContactUpdate


class GetContact:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, contact_id: int) -> ContactRead:
        async with self._uow_factory() as uow:
            result = await uow.contacts.get(contact_id)
        match result:
            case ContactResolved(contact=contact):
                return contact
            case ContactMissing():
                raise ContactNotFound(contact_id)
        raise TypeError(f"unsupported contact resolution: {type(result)!r}")


class CreateContact:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, data: ContactCreate) -> ContactRead:
        async with self._uow_factory() as uow:
            result = await uow.contacts.create(data)
            await uow.commit()
            return result


class UpdateContact:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, contact_id: int, data: ContactUpdate) -> ContactRead:
        async with self._uow_factory() as uow:
            result = await uow.contacts.update(contact_id, data)
            match result:
                case ContactResolved(contact=contact):
                    await uow.commit()
                    return contact
                case ContactMissing():
                    raise ContactNotFound(contact_id)
            raise TypeError(f"unsupported contact resolution: {type(result)!r}")



class DeleteContacts:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        event_publisher: EventPublisher,
    ) -> None:
        self._uow_factory = uow_factory
        self._event_publisher = event_publisher

    async def execute(
        self,
        batch: ContactDeletionBatch,
    ) -> ContactDeletionApplied:
        await self._event_publisher.publish(
            EventDispatchRequest(
                event=EventKey(
                    app_id=AppId("contacts"),
                    name=EventName("delete"),
                ),
                payload=ContactsDeleteEventPayload(
                    contact_ids=batch.contact_ids,
                ),
            )
        )

        async with self._uow_factory() as uow:
            result = await uow.contacts.delete_batch(batch)
            await uow.commit()
            return result
