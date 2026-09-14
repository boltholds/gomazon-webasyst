from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from gomazon_webasyst.contracts.contacts import ContactCreate, ContactMissing, ContactRead, ContactResolution, ContactResolved, ContactUpdate

from .mappings import contact_row_to_read
from .models import WaContactRow


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
