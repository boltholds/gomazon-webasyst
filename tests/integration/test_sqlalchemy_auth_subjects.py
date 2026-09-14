from datetime import datetime

import pytest

pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from gomazon_webasyst.contracts.auth import SubjectResolved, SubjectResolutionError
from gomazon_webasyst.contracts.enums import SubjectResolutionErrorType
from gomazon_webasyst.infrastructure.auth.subjects import SQLAlchemyAuthSubjectStore
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import WaContactRow


@pytest.mark.asyncio
async def test_subject_store_returns_explicit_missing_and_disabled_results():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        session.add_all(
            [
                WaContactRow(
                    id=1,
                    name="Active",
                    login="active",
                    password="hash",
                    is_user=1,
                    create_datetime=datetime(2026, 1, 1),
                ),
                WaContactRow(
                    id=2,
                    name="Disabled",
                    login="disabled",
                    password="hash",
                    is_user=0,
                    create_datetime=datetime(2026, 1, 2),
                ),
            ]
        )
        await session.commit()

    store = SQLAlchemyAuthSubjectStore(factory)
    active = await store.get(1)
    disabled = await store.get(2)
    missing = await store.get(999)

    assert isinstance(active, SubjectResolved)
    assert active.identity.login == "active"
    assert isinstance(disabled, SubjectResolutionError)
    assert disabled.type is SubjectResolutionErrorType.DISABLED
    assert isinstance(missing, SubjectResolutionError)
    assert missing.type is SubjectResolutionErrorType.NOT_FOUND
    await engine.dispose()
