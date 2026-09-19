from dataclasses import dataclass
from typing import Protocol

from gomazon_webasyst.application.team_directory.entities.group import TeamGroup
from gomazon_webasyst.application.team_directory.entities.user_candidate import (
    TeamUserCandidate,
)
from gomazon_webasyst.application.team_directory.vo.filters import TeamUserScope


@dataclass(slots=True, frozen=True)
class TeamUserCandidateSnapshot:
    users: tuple[TeamUserCandidate, ...]


@dataclass(slots=True, frozen=True)
class TeamGroupSnapshot:
    groups: tuple[TeamGroup, ...]


class TeamDirectoryReader(Protocol):
    async def list_users(
        self,
        scope: TeamUserScope,
    ) -> TeamUserCandidateSnapshot: ...

    async def list_groups(self) -> TeamGroupSnapshot: ...
