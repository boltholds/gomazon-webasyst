from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.access_values import AppId, GroupId
from gomazon_webasyst.application.ports.team_group_visibility import (
    TeamPrincipalGroupRightsReader,
)
from gomazon_webasyst.application.ports.team_user_access import (
    TeamUserAppAccessReader,
    TeamUserAppAccessSnapshot,
)
from gomazon_webasyst.application.team_directory.vo.access import (
    TeamGroupManagementRight,
    TeamPrincipalGroupRights,
    TeamUserAppAccess,
)
from gomazon_webasyst.application.team_directory.vo.states import (
    TeamIntMissing,
    TeamIntValue,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaContactRightRow,
    WaUserGroupRow,
)


_GLOBAL_APP = "webasyst"
_TEAM_APP = "team"
_BACKEND = "backend"
_GROUP_PREFIX = "manage_users_in_group."
_UNLIMITED = 2**63 - 1


class SQLAlchemyTeamUserAppAccessReader(TeamUserAppAccessReader):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def read(
        self,
        contact_ids: tuple[int, ...],
        app_ids: tuple[AppId, ...],
    ) -> TeamUserAppAccessSnapshot:
        if not contact_ids or not app_ids:
            return TeamUserAppAccessSnapshot(())

        requested = tuple(dict.fromkeys(app_ids))
        query_apps = tuple(
            dict.fromkeys(
                [app_id.value for app_id in requested] + [_GLOBAL_APP]
            )
        )
        values: dict[tuple[int, str], int] = {}

        async with self._session_factory() as session:
            personal_rows = (
                await session.execute(
                    select(WaContactRightRow).where(
                        WaContactRightRow.group_id.in_(
                            tuple(-contact_id for contact_id in contact_ids)
                        ),
                        WaContactRightRow.app_id.in_(query_apps),
                        WaContactRightRow.name == _BACKEND,
                    )
                )
            ).scalars()
            for row in personal_rows:
                contact_id = -row.group_id
                key = (contact_id, row.app_id)
                values[key] = max(values.get(key, row.value), row.value)

            group_rows = await session.execute(
                select(
                    WaUserGroupRow.contact_id,
                    WaContactRightRow.app_id,
                    WaContactRightRow.value,
                )
                .join(
                    WaContactRightRow,
                    WaContactRightRow.group_id == WaUserGroupRow.group_id,
                )
                .where(
                    WaUserGroupRow.contact_id.in_(contact_ids),
                    WaContactRightRow.app_id.in_(query_apps),
                    WaContactRightRow.name == _BACKEND,
                )
            )
            for contact_id, app_id, value in group_rows:
                key = (contact_id, app_id)
                values[key] = max(values.get(key, value), value)

        result: list[TeamUserAppAccess] = []
        for contact_id in contact_ids:
            global_value = values.get((contact_id, _GLOBAL_APP), 0)
            for app_id in requested:
                if app_id.value != _GLOBAL_APP and global_value > 0:
                    value = _UNLIMITED
                else:
                    value = values.get((contact_id, app_id.value), 0)
                result.append(
                    TeamUserAppAccess(
                        contact_id=contact_id,
                        app_id=app_id,
                        value=value,
                    )
                )
        return TeamUserAppAccessSnapshot(tuple(result))


class SQLAlchemyTeamPrincipalGroupRightsReader(
    TeamPrincipalGroupRightsReader
):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def read(
        self,
        principal_contact_id: int,
        group_ids: tuple[GroupId, ...],
    ) -> TeamPrincipalGroupRights:
        async with self._session_factory() as session:
            memberships = tuple(
                (
                    await session.execute(
                        select(WaUserGroupRow.group_id).where(
                            WaUserGroupRow.contact_id == principal_contact_id
                        )
                    )
                ).scalars()
            )
            principals = (
                -principal_contact_id,
                0,
                *memberships,
            )
            rows = (
                await session.execute(
                    select(WaContactRightRow).where(
                        WaContactRightRow.group_id.in_(principals),
                        WaContactRightRow.app_id.in_(
                            (_GLOBAL_APP, _TEAM_APP)
                        ),
                    )
                )
            ).scalars()

        values: dict[tuple[str, str], int] = {}
        for row in rows:
            key = (row.app_id, row.name)
            values[key] = max(values.get(key, row.value), row.value)

        global_backend = values.get((_GLOBAL_APP, _BACKEND), 0)
        team_backend = values.get((_TEAM_APP, _BACKEND), 0)
        is_team_admin = global_backend > 0 or team_backend >= 2

        if is_team_admin or team_backend <= 0:
            return TeamPrincipalGroupRights(
                principal_contact_id=principal_contact_id,
                is_team_admin=is_team_admin,
                rights=(),
                all_groups_fallback=TeamIntMissing(),
            )

        rights: list[TeamGroupManagementRight] = []
        requested = set(group_ids)
        for (app_id, name), value in values.items():
            if app_id != _TEAM_APP or not name.startswith(_GROUP_PREFIX):
                continue
            suffix = name.removeprefix(_GROUP_PREFIX)
            if suffix == "all":
                continue
            if not suffix.isdigit():
                continue
            group_id = GroupId(int(suffix))
            if group_id in requested:
                rights.append(
                    TeamGroupManagementRight(
                        group_id=group_id,
                        value=value,
                    )
                )

        fallback_value = values.get((_TEAM_APP, _GROUP_PREFIX + "all"))
        fallback = (
            TeamIntMissing()
            if fallback_value is None
            else TeamIntValue(fallback_value)
        )
        rights.sort(key=lambda item: item.group_id.value)
        return TeamPrincipalGroupRights(
            principal_contact_id=principal_contact_id,
            is_team_admin=False,
            rights=tuple(rights),
            all_groups_fallback=fallback,
        )
