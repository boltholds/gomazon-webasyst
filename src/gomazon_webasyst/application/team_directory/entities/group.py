from dataclasses import dataclass

from gomazon_webasyst.application.access_values import GroupId
from gomazon_webasyst.application.team_directory.vo.states import TeamTextState
from gomazon_webasyst.contracts.enums import GroupType


@dataclass(slots=True, frozen=True)
class TeamGroup:
    id: GroupId
    name: str
    count: int
    type: GroupType
    description: TeamTextState
    sort: int

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Team group name must not be empty")
        if self.count < 0:
            raise ValueError("Team group count must not be negative")
