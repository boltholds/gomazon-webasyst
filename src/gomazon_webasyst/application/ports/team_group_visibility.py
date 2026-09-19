from typing import Protocol

from gomazon_webasyst.application.access_values import GroupId
from gomazon_webasyst.application.team_directory.vo.access import (
    TeamPrincipalGroupRights,
)


class TeamPrincipalGroupRightsReader(Protocol):
    async def read(
        self,
        principal_contact_id: int,
        group_ids: tuple[GroupId, ...],
    ) -> TeamPrincipalGroupRights: ...
