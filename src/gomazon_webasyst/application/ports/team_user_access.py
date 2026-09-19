from dataclasses import dataclass
from typing import Protocol

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.team_directory.vo.access import TeamUserAppAccess


@dataclass(slots=True, frozen=True)
class TeamUserAppAccessSnapshot:
    accesses: tuple[TeamUserAppAccess, ...]


class TeamUserAppAccessReader(Protocol):
    async def read(
        self,
        contact_ids: tuple[int, ...],
        app_ids: tuple[AppId, ...],
    ) -> TeamUserAppAccessSnapshot: ...
