from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TypeAlias

from gomazon_webasyst.application.api_execution.vo.activity import ApiUserLastActiveAt, ApiUserNeverActive
from gomazon_webasyst.application.ports.api_activity import (
    ApiActivityFound,
    ApiActivitySubjectMissing,
    ApiActivityTouchMissing,
    ApiUserActivityStore,
)


@dataclass(slots=True, frozen=True)
class ApiActivityUpdated:
    contact_id: int
    at: datetime


@dataclass(slots=True, frozen=True)
class ApiActivitySkipped:
    contact_id: int


ApiActivityServiceResult: TypeAlias = (
    ApiActivityUpdated | ApiActivitySkipped | ApiActivitySubjectMissing
)


class ApiUserActivityService:
    def __init__(
        self,
        store: ApiUserActivityStore,
        *,
        clock: Callable[[], datetime],
        threshold: timedelta = timedelta(seconds=30),
    ) -> None:
        self._store = store
        self._clock = clock
        self._threshold = threshold

    async def touch_if_due(self, contact_id: int) -> ApiActivityServiceResult:
        resolved = await self._store.resolve(contact_id)
        if isinstance(resolved, ApiActivitySubjectMissing):
            return resolved
        state = resolved.state
        if isinstance(state, ApiUserNeverActive):
            return ApiActivitySkipped(contact_id=contact_id)
        now = self._clock()
        if now - state.at <= self._threshold:
            return ApiActivitySkipped(contact_id=contact_id)
        touched = await self._store.touch(contact_id, now)
        if isinstance(touched, ApiActivityTouchMissing):
            return ApiActivitySubjectMissing(contact_id=contact_id)
        return ApiActivityUpdated(contact_id=contact_id, at=now)
