from datetime import datetime

from gomazon_webasyst.application.team_directory.entities.group import TeamGroup
from gomazon_webasyst.application.team_directory.entities.user_candidate import (
    TeamUserCandidate,
)
from gomazon_webasyst.application.team_directory.vo.access import (
    TeamPrincipalGroupRights,
)
from gomazon_webasyst.application.team_directory.vo.filters import (
    TeamAppAccessRequirement,
)
from gomazon_webasyst.application.team_directory.vo.presence import (
    TeamOnlineTimeout,
    TeamPresence,
)
from gomazon_webasyst.application.team_directory.vo.states import (
    TeamDateTimeMissing,
    TeamDateTimeState,
    TeamDateTimeValue,
    TeamIntValue,
)
from gomazon_webasyst.application.ports.team_memberships import (
    TeamMembershipSnapshot,
)
from gomazon_webasyst.application.ports.team_user_access import (
    TeamUserAppAccessSnapshot,
)
from gomazon_webasyst.contracts.enums import TeamAccessLevel, TeamOnlineStatus


class TeamUserVisibilityService:
    def filter(
        self,
        users: tuple[TeamUserCandidate, ...],
        memberships: TeamMembershipSnapshot,
        principal_rights: TeamPrincipalGroupRights,
    ) -> tuple[TeamUserCandidate, ...]:
        if principal_rights.is_team_admin:
            return users

        group_map = {
            entry.contact_id: entry.group_ids
            for entry in memberships.memberships
        }
        hidden = {
            right.group_id
            for right in principal_rights.rights
            if right.value < 0
        }

        visible: list[TeamUserCandidate] = []
        for user in users:
            if user.id == principal_rights.principal_contact_id:
                visible.append(user)
                continue
            groups = group_map.get(user.id, ())
            if not groups:
                visible.append(user)
                continue
            if any(group_id not in hidden for group_id in groups):
                visible.append(user)
        return tuple(visible)


class TeamUserAccessFilterService:
    def filter(
        self,
        users: tuple[TeamUserCandidate, ...],
        requirements: tuple[TeamAppAccessRequirement, ...],
        snapshot: TeamUserAppAccessSnapshot,
    ) -> tuple[TeamUserCandidate, ...]:
        if not requirements:
            return users
        values = {
            (entry.contact_id, entry.app_id): entry.value
            for entry in snapshot.accesses
        }
        result: list[TeamUserCandidate] = []
        for user in users:
            allowed = True
            for requirement in requirements:
                value = values.get((user.id, requirement.app_id), 0)
                if requirement.level is TeamAccessLevel.LIMITED:
                    allowed = value >= 1
                else:
                    allowed = value > 1
                if not allowed:
                    break
            if allowed:
                result.append(user)
        return tuple(result)


class TeamGroupVisibilityService:
    def filter(
        self,
        groups: tuple[TeamGroup, ...],
        principal_rights: TeamPrincipalGroupRights,
    ) -> tuple[TeamGroup, ...]:
        if principal_rights.is_team_admin:
            return groups
        values = {
            item.group_id: item.value
            for item in principal_rights.rights
        }
        fallback = (
            principal_rights.all_groups_fallback.value
            if isinstance(
                principal_rights.all_groups_fallback,
                TeamIntValue,
            )
            else 0
        )
        visible: list[TeamGroup] = []
        for group in groups:
            exact = values.get(group.id, 0)
            effective = exact if exact != 0 else fallback
            if effective >= 0:
                visible.append(group)
        return tuple(visible)


class TeamOnlineStateService:
    def resolve(
        self,
        *,
        last_datetime: TeamDateTimeState,
        presence: TeamPresence,
        now: datetime,
        timeout: TeamOnlineTimeout,
    ) -> TeamOnlineStatus:
        if isinstance(last_datetime, TeamDateTimeMissing):
            return TeamOnlineStatus.OFFLINE
        if not isinstance(last_datetime, TeamDateTimeValue):
            raise AssertionError("unsupported Team last datetime state")

        elapsed = (now - last_datetime.value).total_seconds()
        if elapsed >= timeout.seconds:
            return TeamOnlineStatus.OFFLINE

        if (
            presence.has_open_login
            and isinstance(presence.idle_since, TeamDateTimeValue)
            and (now - presence.idle_since.value).total_seconds() > 60
        ):
            return TeamOnlineStatus.IDLE
        return TeamOnlineStatus.ONLINE
