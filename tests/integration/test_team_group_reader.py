import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.contracts.team import (
    TeamGroupDescriptionMissing,
    TeamGroupDescriptionPresent,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import WaGroupRow
from gomazon_webasyst.infrastructure.team.sqlalchemy.groups import (
    SQLAlchemyTeamGroupReader,
)


@pytest.mark.asyncio
async def test_team_group_reader_preserves_legacy_sort_order_and_nullable_description() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add_all(
            [
                WaGroupRow(
                    id=1,
                    name="Later",
                    cnt=1,
                    icon=None,
                    sort=20,
                    type="group",
                    description="Text",
                ),
                WaGroupRow(
                    id=2,
                    name="Earlier",
                    cnt=2,
                    icon=None,
                    sort=10,
                    type="location",
                    description=None,
                ),
            ]
        )
        await session.commit()

    groups = await SQLAlchemyTeamGroupReader(sessions).list_ordered_by_sort()

    assert tuple(group.id for group in groups) == (2, 1)
    assert isinstance(groups[0].description, TeamGroupDescriptionMissing)
    assert groups[1].description == TeamGroupDescriptionPresent(value="Text")
    await engine.dispose()
