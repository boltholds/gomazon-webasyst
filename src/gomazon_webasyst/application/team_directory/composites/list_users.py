from dataclasses import dataclass

from gomazon_webasyst.application.ports.installed_application_catalog import (
    InstalledApplicationCatalog,
    InstalledApplicationMissing,
)
from gomazon_webasyst.application.ports.team_clock import TeamClock
from gomazon_webasyst.application.ports.team_current_events import (
    TeamCurrentEventReader,
)
from gomazon_webasyst.application.ports.team_directory import TeamDirectoryReader
from gomazon_webasyst.application.ports.team_group_visibility import (
    TeamPrincipalGroupRightsReader,
)
from gomazon_webasyst.application.ports.team_memberships import TeamMembershipReader
from gomazon_webasyst.application.ports.team_presence import TeamPresenceReader
from gomazon_webasyst.application.ports.team_user_access import (
    TeamUserAppAccessReader,
    TeamUserAppAccessSnapshot,
)
from gomazon_webasyst.application.team_directory.entities.user import TeamUser
from gomazon_webasyst.application.team_directory.services.policies import (
    TeamOnlineStateService,
    TeamUserAccessFilterService,
    TeamUserVisibilityService,
)
from gomazon_webasyst.application.team_directory.vo.filters import TeamUsersFilter
from gomazon_webasyst.application.team_directory.vo.presence import (
    TeamOnlineTimeout,
    TeamPresence,
)
from gomazon_webasyst.application.team_directory.vo.states import (
    TeamCurrentEventMissing,
)


@dataclass(slots=True, frozen=True)
class TeamUsersListed:
    users: tuple[TeamUser, ...]


class ListTeamUsers:
    def __init__(
        self,
        *,
        directory: TeamDirectoryReader,
        memberships: TeamMembershipReader,
        user_access: TeamUserAppAccessReader,
        principal_group_rights: TeamPrincipalGroupRightsReader,
        presence: TeamPresenceReader,
        current_events: TeamCurrentEventReader,
        installed_applications: InstalledApplicationCatalog,
        clock: TeamClock,
        online_timeout: TeamOnlineTimeout,
    ) -> None:
        self._directory = directory
        self._memberships = memberships
        self._user_access = user_access
        self._principal_group_rights = principal_group_rights
        self._presence = presence
        self._current_events = current_events
        self._installed_applications = installed_applications
        self._clock = clock
        self._online_timeout = online_timeout
        self._visibility = TeamUserVisibilityService()
        self._access_filter = TeamUserAccessFilterService()
        self._online = TeamOnlineStateService()

    async def __call__(
        self,
        principal_contact_id: int,
        filters: TeamUsersFilter,
    ) -> TeamUsersListed:
        candidates = (await self._directory.list_users(filters.scope)).users
        if not candidates:
            return TeamUsersListed(())

        ids = tuple(user.id for user in candidates)
        memberships = await self._memberships.for_users(ids)
        all_group_ids = tuple(
            dict.fromkeys(
                group_id
                for membership in memberships.memberships
                for group_id in membership.group_ids
            )
        )
        principal_rights = await self._principal_group_rights.read(
            principal_contact_id,
            all_group_ids,
        )
        visible = self._visibility.filter(
            candidates,
            memberships,
            principal_rights,
        )
        if not visible:
            return TeamUsersListed(())

        for requirement in filters.access:
            resolved = await self._installed_applications.resolve(
                requirement.app_id
            )
            if isinstance(resolved, InstalledApplicationMissing):
                return TeamUsersListed(())

        if filters.access:
            access_snapshot = await self._user_access.read(
                tuple(user.id for user in visible),
                tuple(requirement.app_id for requirement in filters.access),
            )
        else:
            access_snapshot = TeamUserAppAccessSnapshot(())
        filtered = self._access_filter.filter(
            visible,
            filters.access,
            access_snapshot,
        )
        if not filtered:
            return TeamUsersListed(())

        final_ids = tuple(user.id for user in filtered)
        presence_snapshot = await self._presence.read(final_ids)
        now = self._clock.now()
        event_snapshot = await self._current_events.current_for_users(
            final_ids,
            now,
        )

        membership_map = {
            item.contact_id: item.group_ids
            for item in memberships.memberships
        }
        presence_map = {
            item.contact_id: item
            for item in presence_snapshot.entries
        }
        event_map = {
            item.contact_id: item.state
            for item in event_snapshot.entries
        }

        users: list[TeamUser] = []
        for candidate in filtered:
            presence = presence_map[candidate.id]
            users.append(
                TeamUser(
                    id=candidate.id,
                    name=candidate.name,
                    firstname=candidate.firstname,
                    lastname=candidate.lastname,
                    middlename=candidate.middlename,
                    company=candidate.company,
                    login=candidate.login,
                    emails=candidate.emails,
                    phones=candidate.phones,
                    locale=candidate.locale,
                    jobtitle=candidate.jobtitle,
                    last_datetime=candidate.last_datetime,
                    birth_day=candidate.birth_day,
                    birth_month=candidate.birth_month,
                    create_datetime=candidate.create_datetime,
                    photo_stamp=candidate.photo_stamp,
                    group_ids=membership_map.get(candidate.id, ()),
                    online_status=self._online.resolve(
                        last_datetime=candidate.last_datetime,
                        presence=presence,
                        now=now,
                        timeout=self._online_timeout,
                    ),
                    current_event=event_map.get(
                        candidate.id,
                        TeamCurrentEventMissing(),
                    ),
                )
            )
        return TeamUsersListed(tuple(users))
