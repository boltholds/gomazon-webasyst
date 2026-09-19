from dataclasses import dataclass
from datetime import datetime

from gomazon_webasyst.application.team_directory.vo.contact import (
    TeamEmailAddress,
    TeamPhone,
)
from gomazon_webasyst.application.team_directory.vo.states import (
    TeamDateTimeState,
    TeamIntState,
)


@dataclass(slots=True, frozen=True)
class TeamUserCandidate:
    id: int
    name: str
    firstname: str
    lastname: str
    middlename: str
    company: str
    login: str
    emails: tuple[TeamEmailAddress, ...]
    phones: tuple[TeamPhone, ...]
    locale: str
    jobtitle: str
    last_datetime: TeamDateTimeState
    birth_day: TeamIntState
    birth_month: TeamIntState
    create_datetime: datetime
    photo_stamp: int

    def __post_init__(self) -> None:
        if self.id <= 0:
            raise ValueError("Team user candidate id must be positive")
        if not self.name:
            raise ValueError("Team user candidate name must not be empty")
        if self.photo_stamp < 0:
            raise ValueError("Team user photo stamp must not be negative")
