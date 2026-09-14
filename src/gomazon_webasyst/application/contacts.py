from gomazon_webasyst.application.errors import ContactNotFound
from gomazon_webasyst.application.ports.unit_of_work import UnitOfWorkFactory
from gomazon_webasyst.contracts.contacts import ContactCreate, ContactRead, ContactUpdate


class GetContact:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, contact_id: int) -> ContactRead:
        async with self._uow_factory() as uow:
            result = await uow.contacts.get(contact_id)
        if result is None:
            raise ContactNotFound(contact_id)
        return result


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
            if result is None:
                raise ContactNotFound(contact_id)
            await uow.commit()
            return result
