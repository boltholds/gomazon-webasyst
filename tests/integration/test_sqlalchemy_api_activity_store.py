from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.application.api_execution.vo.activity import ApiUserLastActiveAt, ApiUserNeverActive
from gomazon_webasyst.application.ports.api_activity import ApiActivityFound, ApiActivityTouched
from gomazon_webasyst.infrastructure.api_execution.activity import SQLAlchemyApiUserActivityStore
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import WaContactRow


@pytest.mark.asyncio
async def test_sqlalchemy_activity_store_normalizes_null_and_persists_touch() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async with sessions() as session:
        session.add(WaContactRow(
            id=42,
            name="User",
            firstname="User",
            is_user=1,
            create_datetime=datetime(2026, 9, 19, 10, 0, 0),
            last_datetime=None,
        ))
        await session.commit()

    store = SQLAlchemyApiUserActivityStore(sessions)
    resolved = await store.resolve(42)
    assert isinstance(resolved, ApiActivityFound)
    assert isinstance(resolved.state, ApiUserNeverActive)

    at = datetime(2026, 9, 19, 12, 0, 0)
    touched = await store.touch(42, at)
    assert isinstance(touched, ApiActivityTouched)

    resolved_after = await store.resolve(42)
    assert isinstance(resolved_after, ApiActivityFound)
    assert resolved_after.state == ApiUserLastActiveAt(at)

    await engine.dispose()
