from sqlalchemy.ext.asyncio import AsyncSession

from gomazon_webasyst.application.ports.access_subjects import (
    AccessSubjectMissing,
    AccessSubjectNotUser,
    AccessSubjectResolution,
    AccessSubjectResolved,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import WaContactRow


class SQLAlchemyAccessSubjectStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve(self, contact_id: int) -> AccessSubjectResolution:
        row = await self._session.get(WaContactRow, contact_id)
        if row is None:
            return AccessSubjectMissing(contact_id)
        if row.is_user <= 0:
            return AccessSubjectNotUser(contact_id)
        return AccessSubjectResolved(contact_id)
