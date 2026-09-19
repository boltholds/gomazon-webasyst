from dataclasses import dataclass
from datetime import datetime
from typing import TypeAlias


@dataclass(slots=True, frozen=True)
class ApiUserNeverActive:
    pass


@dataclass(slots=True, frozen=True)
class ApiUserLastActiveAt:
    at: datetime


ApiUserActivityState: TypeAlias = ApiUserNeverActive | ApiUserLastActiveAt
