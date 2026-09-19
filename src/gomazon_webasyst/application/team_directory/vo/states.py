from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, TypeAlias

from gomazon_webasyst.contracts.enums import (
    TeamCurrentEventKind,
    TeamValueStateKind,
)


@dataclass(slots=True, frozen=True)
class TeamTextMissing:
    kind: TeamValueStateKind = field(init=False, default=TeamValueStateKind.MISSING)


@dataclass(slots=True, frozen=True)
class TeamTextValue:
    value: str
    kind: TeamValueStateKind = field(init=False, default=TeamValueStateKind.PRESENT)


TeamTextState: TypeAlias = TeamTextMissing | TeamTextValue


@dataclass(slots=True, frozen=True)
class TeamIntMissing:
    kind: TeamValueStateKind = field(init=False, default=TeamValueStateKind.MISSING)


@dataclass(slots=True, frozen=True)
class TeamIntValue:
    value: int
    kind: TeamValueStateKind = field(init=False, default=TeamValueStateKind.PRESENT)


TeamIntState: TypeAlias = TeamIntMissing | TeamIntValue


@dataclass(slots=True, frozen=True)
class TeamDateTimeMissing:
    kind: TeamValueStateKind = field(init=False, default=TeamValueStateKind.MISSING)


@dataclass(slots=True, frozen=True)
class TeamDateTimeValue:
    value: datetime
    kind: TeamValueStateKind = field(init=False, default=TeamValueStateKind.PRESENT)


TeamDateTimeState: TypeAlias = TeamDateTimeMissing | TeamDateTimeValue


@dataclass(slots=True, frozen=True)
class TeamCurrentEventMissing:
    kind: TeamCurrentEventKind = field(
        init=False,
        default=TeamCurrentEventKind.MISSING,
    )


@dataclass(slots=True, frozen=True)
class TeamCurrentEventPresent:
    event: "TeamCurrentEvent"
    kind: TeamCurrentEventKind = field(
        init=False,
        default=TeamCurrentEventKind.PRESENT,
    )


TeamCurrentEventState: TypeAlias = (
    TeamCurrentEventMissing | TeamCurrentEventPresent
)

if TYPE_CHECKING:
    from gomazon_webasyst.application.team_directory.entities.current_event import (
        TeamCurrentEvent,
    )
