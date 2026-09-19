from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.access_values import GroupId
from gomazon_webasyst.application.ports.team_directory import (
    TeamDirectoryReader,
    TeamGroupSnapshot,
    TeamUserCandidateSnapshot,
)
from gomazon_webasyst.application.team_directory.entities.group import TeamGroup
from gomazon_webasyst.application.team_directory.entities.user_candidate import (
    TeamUserCandidate,
)
from gomazon_webasyst.application.team_directory.vo.contact import (
    TeamEmailAddress,
    TeamPhone,
)
from gomazon_webasyst.application.team_directory.vo.filters import (
    AllTeamUsers,
    TeamUsersInGroups,
    TeamUserScope,
)
from gomazon_webasyst.contracts.enums import GroupType
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaContactDataRow,
    WaContactEmailRow,
    WaContactRow,
    WaGroupRow,
    WaUserGroupRow,
)
from gomazon_webasyst.infrastructure.team_directory.sqlalchemy.states import (
    datetime_state,
    int_state,
    text_state,
)


class SQLAlchemyTeamDirectoryReader(TeamDirectoryReader):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def list_users(
        self,
        scope: TeamUserScope,
    ) -> TeamUserCandidateSnapshot:
        async with self._session_factory() as session:
            statement = select(WaContactRow).where(
                WaContactRow.login.is_not(None),
                WaContactRow.is_user == 1,
            )
            if isinstance(scope, TeamUsersInGroups):
                statement = (
                    statement.join(
                        WaUserGroupRow,
                        WaUserGroupRow.contact_id == WaContactRow.id,
                    )
                    .where(
                        WaUserGroupRow.group_id.in_(
                            tuple(group_id.value for group_id in scope.group_ids)
                        )
                    )
                    .distinct()
                )
            elif not isinstance(scope, AllTeamUsers):
                raise AssertionError("unsupported Team user scope")
            statement = statement.order_by(WaContactRow.name, WaContactRow.id)
            rows = tuple((await session.execute(statement)).scalars())
            if not rows:
                return TeamUserCandidateSnapshot(())

            contact_ids = tuple(row.id for row in rows)
            email_map = await self._emails(session, contact_ids)
            phone_map = await self._phones(session, contact_ids)

            return TeamUserCandidateSnapshot(
                tuple(
                    TeamUserCandidate(
                        id=row.id,
                        name=row.name,
                        firstname=row.firstname,
                        lastname=row.lastname,
                        middlename=row.middlename,
                        company=row.company,
                        login=row.login or "",
                        emails=email_map.get(row.id, ()),
                        phones=phone_map.get(row.id, ()),
                        locale=row.locale,
                        jobtitle=row.jobtitle,
                        last_datetime=datetime_state(row.last_datetime),
                        birth_day=int_state(row.birth_day),
                        birth_month=int_state(row.birth_month),
                        create_datetime=row.create_datetime,
                        photo_stamp=row.photo,
                    )
                    for row in rows
                )
            )

    async def list_groups(self) -> TeamGroupSnapshot:
        async with self._session_factory() as session:
            rows = tuple(
                (
                    await session.execute(
                        select(WaGroupRow).order_by(
                            WaGroupRow.sort,
                            WaGroupRow.id,
                        )
                    )
                ).scalars()
            )
            return TeamGroupSnapshot(
                tuple(
                    TeamGroup(
                        id=GroupId(row.id),
                        name=row.name,
                        count=row.cnt,
                        type=GroupType(row.type),
                        description=text_state(row.description),
                        sort=row.sort if row.sort is not None else 0,
                    )
                    for row in rows
                )
            )

    @staticmethod
    async def _emails(
        session: AsyncSession,
        contact_ids: tuple[int, ...],
    ) -> dict[int, tuple[TeamEmailAddress, ...]]:
        rows = (
            await session.execute(
                select(WaContactEmailRow)
                .where(WaContactEmailRow.contact_id.in_(contact_ids))
                .order_by(
                    WaContactEmailRow.contact_id,
                    WaContactEmailRow.sort,
                    WaContactEmailRow.id,
                )
            )
        ).scalars()
        result: dict[int, list[TeamEmailAddress]] = {}
        for row in rows:
            result.setdefault(row.contact_id, []).append(
                TeamEmailAddress(row.email)
            )
        return {key: tuple(value) for key, value in result.items()}

    @staticmethod
    async def _phones(
        session: AsyncSession,
        contact_ids: tuple[int, ...],
    ) -> dict[int, tuple[TeamPhone, ...]]:
        rows = (
            await session.execute(
                select(WaContactDataRow)
                .where(
                    WaContactDataRow.contact_id.in_(contact_ids),
                    WaContactDataRow.field == "phone",
                )
                .order_by(
                    WaContactDataRow.contact_id,
                    WaContactDataRow.sort,
                    WaContactDataRow.id,
                )
            )
        ).scalars()
        result: dict[int, list[TeamPhone]] = {}
        for row in rows:
            result.setdefault(row.contact_id, []).append(
                TeamPhone(
                    value=row.value,
                    ext=row.ext,
                    status=text_state(row.status),
                )
            )
        return {key: tuple(value) for key, value in result.items()}
