from dataclasses import dataclass

from gomazon_webasyst.application.access_values import GroupId
from gomazon_webasyst.application.team_directory.vo.states import TeamTextState


@dataclass(slots=True, frozen=True)
class TeamEmailAddress:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("Team email address must not be empty")


@dataclass(slots=True, frozen=True)
class TeamPhone:
    value: str
    ext: str
    status: TeamTextState

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("Team phone value must not be empty")


@dataclass(slots=True, frozen=True)
class TeamUserMemberships:
    contact_id: int
    group_ids: tuple[GroupId, ...]

    def __post_init__(self) -> None:
        if self.contact_id <= 0:
            raise ValueError("Team membership contact id must be positive")
        if len(self.group_ids) != len(set(self.group_ids)):
            raise ValueError("duplicate Team membership group id")
