from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from gomazon_webasyst.application.contacts import CreateContact, GetContact, UpdateContact
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.factory import create_engine, create_uow_factory


@dataclass(slots=True)
class Container:
    settings: Settings
    engine: AsyncEngine
    get_contact: GetContact
    create_contact: CreateContact
    update_contact: UpdateContact

    async def close(self) -> None:
        await self.engine.dispose()


def create_container(settings: Settings) -> Container:
    engine = create_engine(settings)
    uow_factory = create_uow_factory(engine)
    return Container(
        settings=settings,
        engine=engine,
        get_contact=GetContact(uow_factory),
        create_contact=CreateContact(uow_factory),
        update_contact=UpdateContact(uow_factory),
    )
