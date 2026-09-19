from dataclasses import dataclass

from gomazon_webasyst.application.team_directory.vo.states import TeamDateTimeState


@dataclass(slots=True, frozen=True)
class TeamOnlineTimeout:
    seconds: int

    def __post_init__(self) -> None:
        if self.seconds <= 0:
            raise ValueError("Team online timeout must be positive")


@dataclass(slots=True, frozen=True)
class TeamPresence:
    contact_id: int
    has_open_login: bool
    idle_since: TeamDateTimeState

    def __post_init__(self) -> None:
        if self.contact_id <= 0:
            raise ValueError("Team presence contact id must be positive")
