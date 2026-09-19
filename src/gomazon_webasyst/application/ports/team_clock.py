from datetime import datetime
from typing import Protocol


class TeamClock(Protocol):
    def now(self) -> datetime: ...
