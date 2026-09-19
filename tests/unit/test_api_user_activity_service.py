from datetime import datetime, timedelta

import pytest

from gomazon_webasyst.application.api_execution.services.activity import (
    ApiActivitySkipped,
    ApiActivityUpdated,
    ApiUserActivityService,
)
from gomazon_webasyst.application.api_execution.vo.activity import (
    ApiUserLastActiveAt,
    ApiUserNeverActive,
)
from gomazon_webasyst.application.ports.api_activity import (
    ApiActivityFound,
    ApiActivityTouched,
)


NOW = datetime(2026, 9, 19, 12, 0, 0)


class Store:
    def __init__(self, state):
        self.state = state
        self.touches = []

    async def resolve(self, contact_id):
        return ApiActivityFound(contact_id=contact_id, state=self.state)

    async def touch(self, contact_id, at):
        self.touches.append((contact_id, at))
        self.state = ApiUserLastActiveAt(at)
        return ApiActivityTouched(contact_id=contact_id, at=at)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state",
    [
        ApiUserNeverActive(),
        ApiUserLastActiveAt(NOW - timedelta(seconds=30)),
        ApiUserLastActiveAt(NOW - timedelta(seconds=29)),
    ],
)
async def test_activity_is_not_touched_until_strictly_older_than_30_seconds(state) -> None:
    store = Store(state)
    service = ApiUserActivityService(store, clock=lambda: NOW, threshold=timedelta(seconds=30))
    result = await service.touch_if_due(42)
    assert isinstance(result, ApiActivitySkipped)
    assert store.touches == []


@pytest.mark.asyncio
async def test_activity_older_than_30_seconds_is_touched() -> None:
    store = Store(ApiUserLastActiveAt(NOW - timedelta(seconds=31)))
    service = ApiUserActivityService(store, clock=lambda: NOW, threshold=timedelta(seconds=30))
    result = await service.touch_if_due(42)
    assert isinstance(result, ApiActivityUpdated)
    assert store.touches == [(42, NOW)]
