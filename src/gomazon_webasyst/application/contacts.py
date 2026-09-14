from gomazon_webasyst.application.errors import ContactNotFound
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
