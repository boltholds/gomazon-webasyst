from gomazon_webasyst.application.access_values import (
    AppId,
    GroupId,
    GroupTarget,
    GuestsTarget,
    UserTarget,
)
from gomazon_webasyst.application.ports.access_control_uow import (
    AccessControlUnitOfWorkFactory,
)
from gomazon_webasyst.application.ports.installed_application_catalog import (
    InstalledApplicationCatalog,
    InstalledApplicationMissing,
)
from gomazon_webasyst.application.ports.rights import NamedRightAssignment
from gomazon_webasyst.application.rights_evaluator import RightsEvaluator
from gomazon_webasyst.application.team.ports import TeamUserReader
from gomazon_webasyst.contracts.access_control import (
    FullAppAccess,
    GlobalAdminAccess,
    LimitedAppAccess,
)
from gomazon_webasyst.contracts.enums import TeamUserAccessLevel
from gomazon_webasyst.contracts.team import (
    TeamUserAccessRequirement,
    TeamUserFilter,
    TeamUserRead,
)


_TEAM_APP_ID = AppId("team")
_MANAGE_USERS_PREFIX = "manage_users_in_group"


class ListVisibleTeamUsers:
    def __init__(
        self,
        *,
        users: TeamUserReader,
        access_uow_factory: AccessControlUnitOfWorkFactory,
        rights_evaluator: RightsEvaluator,
        installed_applications: InstalledApplicationCatalog,
    ) -> None:
        self._users = users
        self._access_uow_factory = access_uow_factory
        self._rights_evaluator = rights_evaluator
        self._installed_applications = installed_applications

    async def execute(
        self,
        *,
        contact_id: int,
        user_filter: TeamUserFilter,
    ) -> tuple[TeamUserRead, ...]:
        candidates = await self._users.list_candidates(user_filter.group_ids)
        if not candidates:
            return ()

        if not await self._access_apps_are_installed(user_filter.access):
            return ()

        async with self._access_uow_factory() as uow:
            actor_memberships = await uow.memberships.list_for_user(contact_id)
            actor_targets = (
                UserTarget(contact_id),
                *(GroupTarget(item.group_id) for item in actor_memberships),
                GuestsTarget(),
            )
            actor_snapshot = await uow.rights.load_for_targets(actor_targets)
            actor_access = self._rights_evaluator.app_access(
                actor_snapshot,
                _TEAM_APP_ID,
            )
            actor_is_admin = isinstance(
                actor_access,
                FullAppAccess | GlobalAdminAccess,
            )

            hidden_group_ids = (
                frozenset()
                if actor_is_admin
                else self._hidden_group_ids(actor_snapshot, candidates)
            )

            visible: list[TeamUserRead] = []
            for candidate in candidates:
                if not actor_is_admin and not self._is_visible_to_actor(
                    actor_contact_id=contact_id,
                    candidate=candidate,
                    hidden_group_ids=hidden_group_ids,
                ):
                    continue
                if user_filter.access and not await self._candidate_has_access(
                    uow=uow,
                    candidate=candidate,
                    requirements=user_filter.access,
                ):
                    continue
                visible.append(candidate)

        return tuple(visible)

    async def _access_apps_are_installed(
        self,
        requirements: tuple[TeamUserAccessRequirement, ...],
    ) -> bool:
        for requirement in requirements:
            resolution = await self._installed_applications.resolve(
                AppId(requirement.app_id)
            )
            if isinstance(resolution, InstalledApplicationMissing):
                return False
        return True

    @staticmethod
    def _hidden_group_ids(
        actor_snapshot,
        candidates: tuple[TeamUserRead, ...],
    ) -> frozenset[int]:
        candidate_group_ids = {
            group_id
            for candidate in candidates
            for group_id in candidate.group_ids
        }
        effective_exact: dict[int, int] = {}
        prefix = f"{_MANAGE_USERS_PREFIX}."
        for assignment in actor_snapshot.assignments:
            if not isinstance(assignment, NamedRightAssignment):
                continue
            if assignment.key.app_id != _TEAM_APP_ID:
                continue
            name = assignment.key.name.value
            if not name.startswith(prefix):
                continue
            suffix = name[len(prefix):]
            if not suffix.isdecimal():
                continue
            group_id = int(suffix)
            if group_id <= 0 or group_id not in candidate_group_ids:
                continue
            value = assignment.value.value
            if (
                group_id not in effective_exact
                or value > effective_exact[group_id]
            ):
                effective_exact[group_id] = value
        return frozenset(
            group_id
            for group_id, value in effective_exact.items()
            if value < 0
        )

    @staticmethod
    def _is_visible_to_actor(
        *,
        actor_contact_id: int,
        candidate: TeamUserRead,
        hidden_group_ids: frozenset[int],
    ) -> bool:
        if candidate.id == actor_contact_id:
            return True
        if not candidate.group_ids:
            return True
        return any(
            group_id not in hidden_group_ids
            for group_id in candidate.group_ids
        )

    async def _candidate_has_access(
        self,
        *,
        uow,
        candidate: TeamUserRead,
        requirements: tuple[TeamUserAccessRequirement, ...],
    ) -> bool:
        targets = (
            UserTarget(candidate.id),
            *(GroupTarget(GroupId(group_id)) for group_id in candidate.group_ids),
        )
        snapshot = await uow.rights.load_for_targets(targets)
        for requirement in requirements:
            access = self._rights_evaluator.app_access(
                snapshot,
                AppId(requirement.app_id),
            )
            if requirement.level is TeamUserAccessLevel.LIMITED:
                if not isinstance(
                    access,
                    LimitedAppAccess | FullAppAccess | GlobalAdminAccess,
                ):
                    return False
                continue
            assert requirement.level is TeamUserAccessLevel.FULL
            if not isinstance(access, FullAppAccess | GlobalAdminAccess):
                return False
        return True
