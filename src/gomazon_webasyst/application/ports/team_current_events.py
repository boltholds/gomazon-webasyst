from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from gomazon_webasyst.application.team_directory.vo.states import (
    TeamCurrentEventState,
)


@dataclass(slots=True, frozen=True)
class TeamUserCurrentEvent:
    contact_id: int
    state: TeamCurrentEventState

    def __post_init__(self) -> None:
        if self.contact_id <= 0:
            raise ValueError("Team current event contact id must be positive")


@dataclass(slots=True, frozen=True)
class TeamCurrentEventSnapshot:
    entries: tuple[TeamUserCurrentEvent, ...]


class TeamCurrentEventReader(Protocol):
    async def current_for_users(
        self,
        contact_ids: tuple[int, ...],
        now: datetime,
    ) -> TeamCurrentEventSnapshot: ...
