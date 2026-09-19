from dataclasses import dataclass
from typing import Protocol

from gomazon_webasyst.application.team_directory.vo.contact import (
    TeamUserMemberships,
)


@dataclass(slots=True, frozen=True)
class TeamMembershipSnapshot:
    memberships: tuple[TeamUserMemberships, ...]


class TeamMembershipReader(Protocol):
    async def for_users(
        self,
        contact_ids: tuple[int, ...],
    ) -> TeamMembershipSnapshot: ...
