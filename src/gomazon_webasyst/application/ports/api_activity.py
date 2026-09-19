from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.api_execution.vo.activity import ApiUserActivityState


@dataclass(slots=True, frozen=True)
class ApiActivityFound:
    contact_id: int
    state: ApiUserActivityState


@dataclass(slots=True, frozen=True)
class ApiActivitySubjectMissing:
    contact_id: int


ApiActivityResolution: TypeAlias = ApiActivityFound | ApiActivitySubjectMissing


@dataclass(slots=True, frozen=True)
class ApiActivityTouched:
    contact_id: int
    at: datetime


@dataclass(slots=True, frozen=True)
class ApiActivityTouchMissing:
    contact_id: int


ApiActivityTouchResult: TypeAlias = ApiActivityTouched | ApiActivityTouchMissing


class ApiUserActivityStore(Protocol):
    async def resolve(self, contact_id: int) -> ApiActivityResolution: ...
    async def touch(self, contact_id: int, at: datetime) -> ApiActivityTouchResult: ...
