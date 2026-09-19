from gomazon_webasyst.application.access_values import (
    AppId,
    GuestsTarget,
    GroupTarget,
    PermissionKey,
    RightName,
    UserTarget,
)
from gomazon_webasyst.application.ports.access_control_uow import (
    AccessControlUnitOfWorkFactory,
)
from gomazon_webasyst.application.rights_evaluator import RightsEvaluator
from gomazon_webasyst.application.team.ports import TeamGroupReader
from gomazon_webasyst.contracts.access_control import FiniteRight, UnlimitedRight
from gomazon_webasyst.contracts.team import TeamGroupFilter, TeamGroupRead


_TEAM_APP_ID = AppId("team")
_MANAGE_USERS_PREFIX = "manage_users_in_group"


class ListVisibleTeamGroups:
    def __init__(
        self,
        *,
        groups: TeamGroupReader,
        access_uow_factory: AccessControlUnitOfWorkFactory,
        rights_evaluator: RightsEvaluator,
    ) -> None:
        self._groups = groups
        self._access_uow_factory = access_uow_factory
        self._rights_evaluator = rights_evaluator

    async def execute(
        self,
        *,
        contact_id: int,
        group_filter: TeamGroupFilter,
    ) -> tuple[TeamGroupRead, ...]:
        groups = await self._groups.list_ordered_by_sort()

        async with self._access_uow_factory() as uow:
            memberships = await uow.memberships.list_for_user(contact_id)
            targets = (
                UserTarget(contact_id),
                *(GroupTarget(item.group_id) for item in memberships),
                GuestsTarget(),
            )
            snapshot = await uow.rights.load_for_targets(tuple(targets))

        visible: list[TeamGroupRead] = []
        for group in groups:
            if (
                group_filter.types
                and group.type.value not in group_filter.types
            ):
                continue
            right = self._rights_evaluator.effective_right(
                snapshot,
                PermissionKey(
                    _TEAM_APP_ID,
                    RightName(f"{_MANAGE_USERS_PREFIX}.{group.id}"),
                ),
            )
            if isinstance(right, UnlimitedRight):
                visible.append(group)
                continue
            if isinstance(right, FiniteRight) and right.value >= 0:
                visible.append(group)

        return tuple(visible)
