from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.api_execution.vo.activity import ApiUserLastActiveAt, ApiUserNeverActive
from gomazon_webasyst.application.ports.api_activity import (
    ApiActivityFound,
    ApiActivityResolution,
    ApiActivitySubjectMissing,
    ApiActivityTouched,
    ApiActivityTouchMissing,
    ApiActivityTouchResult,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import WaContactRow


class SQLAlchemyApiUserActivityStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def resolve(self, contact_id: int) -> ApiActivityResolution:
        async with self._session_factory() as session:
            row = await session.get(WaContactRow, contact_id)
            if row is None:
                return ApiActivitySubjectMissing(contact_id=contact_id)
            state = (
                ApiUserNeverActive()
                if row.last_datetime is None
                else ApiUserLastActiveAt(at=row.last_datetime)
            )
            return ApiActivityFound(contact_id=contact_id, state=state)

    async def touch(self, contact_id: int, at: datetime) -> ApiActivityTouchResult:
        async with self._session_factory() as session:
            row = await session.get(WaContactRow, contact_id)
            if row is None:
                return ApiActivityTouchMissing(contact_id=contact_id)
            row.last_datetime = at
            await session.commit()
            return ApiActivityTouched(contact_id=contact_id, at=at)
