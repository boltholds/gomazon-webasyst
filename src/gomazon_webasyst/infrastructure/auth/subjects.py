from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.contracts.auth import AuthIdentity, SubjectResolved, SubjectResolution, SubjectResolutionError
from gomazon_webasyst.contracts.enums import SubjectResolutionErrorType
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import WaContactRow


class SQLAlchemyAuthSubjectStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, subject_id: int) -> SubjectResolution:
        async with self._session_factory() as session:
            row = await session.get(WaContactRow, subject_id)
        if row is None:
            return SubjectResolutionError(type=SubjectResolutionErrorType.NOT_FOUND)
        if row.is_user <= 0:
            return SubjectResolutionError(type=SubjectResolutionErrorType.DISABLED)
        return SubjectResolved(
            identity=AuthIdentity(
                id=row.id,
                login=row.login or "",
                password_hash=row.password,
                is_user=row.is_user,
                create_datetime=row.create_datetime,
            )
        )
