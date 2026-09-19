from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.team.ports import TeamGroupReader
from gomazon_webasyst.contracts.team import TeamGroupRead
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import WaGroupRow


class SQLAlchemyTeamGroupReader(TeamGroupReader):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def list_ordered_by_sort(self) -> tuple[TeamGroupRead, ...]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(WaGroupRow).order_by(WaGroupRow.sort)
            )
            return tuple(
                TeamGroupRead(
                    id=row.id,
                    name=row.name,
                    cnt=row.cnt,
                    type=row.type,
                    description=row.description,
                )
                for row in result.scalars()
            )
