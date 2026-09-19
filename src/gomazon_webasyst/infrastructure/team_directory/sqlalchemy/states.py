from datetime import datetime

from gomazon_webasyst.application.team_directory.vo.states import (
    TeamDateTimeMissing,
    TeamDateTimeState,
    TeamDateTimeValue,
    TeamIntMissing,
    TeamIntState,
    TeamIntValue,
    TeamTextMissing,
    TeamTextState,
    TeamTextValue,
)


def text_state(value: str | None) -> TeamTextState:
    if value is None:
        return TeamTextMissing()
    return TeamTextValue(value)


def int_state(value: int | None) -> TeamIntState:
    if value is None:
        return TeamIntMissing()
    return TeamIntValue(value)


def datetime_state(value: datetime | None) -> TeamDateTimeState:
    if value is None:
        return TeamDateTimeMissing()
    return TeamDateTimeValue(value)
