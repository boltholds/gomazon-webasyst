from dataclasses import dataclass

from gomazon_webasyst.application.ports.team_directory import TeamDirectoryReader
from gomazon_webasyst.application.ports.team_group_visibility import (
    TeamPrincipalGroupRightsReader,
)
from gomazon_webasyst.application.team_directory.entities.group import TeamGroup
from gomazon_webasyst.application.team_directory.services.policies import (
    TeamGroupVisibilityService,
)
from gomazon_webasyst.application.team_directory.vo.filters import TeamGroupsFilter


@dataclass(slots=True, frozen=True)
class TeamGroupsListed:
    groups: tuple[TeamGroup, ...]


class ListTeamGroups:
    def __init__(
        self,
        *,
        directory: TeamDirectoryReader,
        principal_group_rights: TeamPrincipalGroupRightsReader,
    ) -> None:
        self._directory = directory
        self._principal_group_rights = principal_group_rights
        self._visibility = TeamGroupVisibilityService()

    async def __call__(
        self,
        principal_contact_id: int,
        filters: TeamGroupsFilter,
    ) -> TeamGroupsListed:
        groups = (await self._directory.list_groups()).groups
        if filters.types:
            groups = tuple(
                group for group in groups
                if group.type in filters.types
            )
        if not groups:
            return TeamGroupsListed(())
        rights = await self._principal_group_rights.read(
            principal_contact_id,
            tuple(group.id for group in groups),
        )
        return TeamGroupsListed(
            self._visibility.filter(groups, rights)
        )
