from sqlalchemy import Column, Integer, MetaData, SmallInteger, Table, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.contact_deletion import ContactDeletionBatch
from gomazon_webasyst.application.contacts_app.ports import (
    ContactsPrivateRightsCleaner,
    ContactsPrivateRightsDeleted,
)


_METADATA = MetaData()
_CONTACTS_RIGHTS = Table(
    "contacts_rights",
    _METADATA,
    Column("group_id", Integer, primary_key=True, nullable=False),
    Column("category_id", Integer, primary_key=True, nullable=False),
    Column("writable", SmallInteger, nullable=False),
)


class SQLAlchemyContactsPrivateRightsCleaner(ContactsPrivateRightsCleaner):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def delete_for_contacts(
        self,
        batch: ContactDeletionBatch,
    ) -> ContactsPrivateRightsDeleted:
        personal_group_ids = tuple(
            -contact_id for contact_id in batch.contact_ids
        )
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(
                    delete(_CONTACTS_RIGHTS).where(
                        _CONTACTS_RIGHTS.c.group_id.in_(personal_group_ids)
                    )
                )
        return ContactsPrivateRightsDeleted(contact_ids=batch.contact_ids)
