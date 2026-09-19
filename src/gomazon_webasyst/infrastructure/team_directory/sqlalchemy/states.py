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


def text_state(value: object) -> TeamTextState:
    if value is None:
        return TeamTextMissing()
    if not isinstance(value, str):
        raise TypeError("legacy text value must be str or database NULL")
    return TeamTextValue(value)


def int_state(value: object) -> TeamIntState:
    if value is None:
        return TeamIntMissing()
    if not isinstance(value, int):
        raise TypeError("legacy int value must be int or database NULL")
    return TeamIntValue(value)


def datetime_state(value: object) -> TeamDateTimeState:
    if value is None:
        return TeamDateTimeMissing()
    if not isinstance(value, datetime):
        raise TypeError("legacy datetime value must be datetime or database NULL")
    return TeamDateTimeValue(value)
