from dataclasses import dataclass
from datetime import datetime

from gomazon_webasyst.application.team_directory.vo.states import TeamTextState


@dataclass(slots=True, frozen=True)
class TeamCurrentEvent:
    id: int
    uid: TeamTextState
    create_datetime: datetime
    update_datetime: datetime
    contact_id: int
    calendar_id: int
    summary: str
    description: TeamTextState
    location: TeamTextState
    start: datetime
    end: datetime
    is_allday: bool
    is_status: bool
    sequence: int
    calendar_name: str
    status_bg_color: TeamTextState
    status_font_color: TeamTextState
    bg_color: TeamTextState
    font_color: TeamTextState
    icon: TeamTextState

    def __post_init__(self) -> None:
        if self.id <= 0 or self.contact_id <= 0 or self.calendar_id <= 0:
            raise ValueError("Team current event ids must be positive")
