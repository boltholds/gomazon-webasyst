from dataclasses import dataclass
from typing import Protocol

from gomazon_webasyst.application.team_directory.vo.presence import TeamPresence


@dataclass(slots=True, frozen=True)
class TeamPresenceSnapshot:
    entries: tuple[TeamPresence, ...]


class TeamPresenceReader(Protocol):
    async def read(
        self,
        contact_ids: tuple[int, ...],
    ) -> TeamPresenceSnapshot: ...
