from datetime import datetime, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from gomazon_webasyst.application.contact_deletion import (
    ContactDeletionApplied,
    ContactDeletionBatch,
)
from gomazon_webasyst.contracts.contacts import ContactCreate, ContactMissing, ContactRead, ContactResolution, ContactResolved, ContactUpdate

from .contact_delete_tables import (
    WA_APP_TOKENS,
    WA_CONTACT_CATEGORIES,
    WA_CONTACT_CATEGORY,
    WA_CONTACT_DATA_TEXT,
    WA_CONTACT_EVENTS,
    WA_CONTACT_SETTINGS,
    WA_VERIFICATION_CHANNEL_ASSETS,
)
from .mappings import contact_row_to_read
from .models import (
    WaContactDataRow,
    WaContactEmailRow,
    WaContactRightRow,
    WaContactRow,
    WaUserGroupRow,
)


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SQLAlchemyContactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, contact_id: int) -> ContactResolution:
        row = await self._session.get(WaContactRow, contact_id)
        if row is None:
            return ContactMissing(contact_id=contact_id)
        return ContactResolved(contact=contact_row_to_read(row))

    async def create(self, data: ContactCreate) -> ContactRead:
        values = data.model_dump()
        values["is_company"] = int(data.is_company)
        row = WaContactRow(
            **values,
            create_datetime=utc_now_naive(),
        )
        self._session.add(row)
        await self._session.flush()
        return contact_row_to_read(row)

    async def update(self, contact_id: int, data: ContactUpdate) -> ContactResolution:
        row = await self._session.get(WaContactRow, contact_id)
        if row is None:
            return ContactMissing(contact_id=contact_id)
        changes = data.model_dump(exclude_unset=True)
        if "is_company" in changes:
            changes["is_company"] = int(changes["is_company"])
        for name, value in changes.items():
            setattr(row, name, value)
        await self._session.flush()
        return ContactResolved(contact=contact_row_to_read(row))


    async def delete_batch(
        self,
        batch: ContactDeletionBatch,
    ) -> ContactDeletionApplied:
        contact_ids = batch.contact_ids
        principal_ids = tuple(-contact_id for contact_id in contact_ids)

        await self._session.execute(
            delete(WaContactRightRow).where(
                WaContactRightRow.group_id.in_(principal_ids)
            )
        )

        await self._clear_verification_assets(contact_ids)

        await self._session.execute(
            delete(WA_CONTACT_SETTINGS).where(
                WA_CONTACT_SETTINGS.c.contact_id.in_(contact_ids)
            )
        )
        await self._session.execute(
            delete(WA_APP_TOKENS).where(
                WA_APP_TOKENS.c.contact_id.in_(contact_ids)
            )
        )
        await self._session.execute(
            delete(WaContactEmailRow).where(
                WaContactEmailRow.contact_id.in_(contact_ids)
            )
        )
        await self._session.execute(
            delete(WaUserGroupRow).where(
                WaUserGroupRow.contact_id.in_(contact_ids)
            )
        )
        await self._session.execute(
            delete(WaContactDataRow).where(
                WaContactDataRow.contact_id.in_(contact_ids)
            )
        )
        await self._session.execute(
            delete(WA_CONTACT_DATA_TEXT).where(
                WA_CONTACT_DATA_TEXT.c.contact_id.in_(contact_ids)
            )
        )

        category_ids = await self._category_ids_for_contacts(contact_ids)
        await self._session.execute(
            delete(WA_CONTACT_CATEGORIES).where(
                WA_CONTACT_CATEGORIES.c.contact_id.in_(contact_ids)
            )
        )
        await self._recalculate_nonempty_category_counters(category_ids)

        await self._session.execute(
            delete(WA_CONTACT_EVENTS).where(
                WA_CONTACT_EVENTS.c.contact_id.in_(contact_ids)
            )
        )

        await self._session.execute(
            update(WaContactRow)
            .where(WaContactRow.company_contact_id.in_(contact_ids))
            .values(company_contact_id=0)
        )
        await self._session.execute(
            delete(WaContactRow).where(
                WaContactRow.id.in_(contact_ids)
            )
        )
        await self._session.flush()

        return ContactDeletionApplied(contact_ids=contact_ids)

    async def _clear_verification_assets(
        self,
        contact_ids: tuple[int, ...],
    ) -> None:
        email_result = await self._session.execute(
            select(WaContactEmailRow.email).where(
                WaContactEmailRow.contact_id.in_(contact_ids)
            )
        )
        data_result = await self._session.execute(
            select(WaContactDataRow.value).where(
                WaContactDataRow.contact_id.in_(contact_ids)
            )
        )
        addresses = tuple(
            dict.fromkeys(
                [
                    *email_result.scalars().all(),
                    *data_result.scalars().all(),
                ]
            )
        )
        if not addresses:
            return
        await self._session.execute(
            delete(WA_VERIFICATION_CHANNEL_ASSETS).where(
                WA_VERIFICATION_CHANNEL_ASSETS.c.address.in_(addresses)
            )
        )

    async def _category_ids_for_contacts(
        self,
        contact_ids: tuple[int, ...],
    ) -> tuple[int, ...]:
        result = await self._session.execute(
            select(WA_CONTACT_CATEGORIES.c.category_id).where(
                WA_CONTACT_CATEGORIES.c.contact_id.in_(contact_ids)
            )
        )
        return tuple(dict.fromkeys(int(value) for value in result.scalars()))

    async def _recalculate_nonempty_category_counters(
        self,
        category_ids: tuple[int, ...],
    ) -> None:
        for category_id in category_ids:
            count_result = await self._session.execute(
                select(func.count())
                .select_from(WA_CONTACT_CATEGORIES)
                .where(
                    WA_CONTACT_CATEGORIES.c.category_id == category_id
                )
            )
            count = int(count_result.scalar_one())
            if count <= 0:
                continue
            await self._session.execute(
                update(WA_CONTACT_CATEGORY)
                .where(WA_CONTACT_CATEGORY.c.id == category_id)
                .values(cnt=count)
            )
