from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.access_values import GroupId
from gomazon_webasyst.application.ports.team_memberships import (
    TeamMembershipReader,
    TeamMembershipSnapshot,
)
from gomazon_webasyst.application.team_directory.vo.contact import (
    TeamUserMemberships,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaUserGroupRow,
)


class SQLAlchemyTeamMembershipReader(TeamMembershipReader):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def for_users(
        self,
        contact_ids: tuple[int, ...],
    ) -> TeamMembershipSnapshot:
        if not contact_ids:
            return TeamMembershipSnapshot(())
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(WaUserGroupRow)
                    .where(WaUserGroupRow.contact_id.in_(contact_ids))
                    .order_by(
                        WaUserGroupRow.contact_id,
                        WaUserGroupRow.group_id,
                    )
                )
            ).scalars()
            by_contact: dict[int, list[GroupId]] = {
                contact_id: [] for contact_id in contact_ids
            }
            for row in rows:
                by_contact[row.contact_id].append(GroupId(row.group_id))
            return TeamMembershipSnapshot(
                tuple(
                    TeamUserMemberships(
                        contact_id=contact_id,
                        group_ids=tuple(by_contact[contact_id]),
                    )
                    for contact_id in contact_ids
                )
            )
