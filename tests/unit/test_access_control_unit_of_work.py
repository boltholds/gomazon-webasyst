import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.infrastructure.access_control.sqlalchemy.unit_of_work import (
    SQLAlchemyAccessControlUnitOfWorkFactory,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base


@pytest.mark.asyncio
async def test_acl_uow_exposes_repositories_only_while_active_and_commits() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = SQLAlchemyAccessControlUnitOfWorkFactory(
        async_sessionmaker(engine, expire_on_commit=False)
    )
    uow = factory()

    with pytest.raises(RuntimeError):
        _ = uow.groups

    async with uow:
        assert uow.groups is not None
        assert uow.memberships is not None
        assert uow.rights is not None
        assert uow.subjects is not None
        await uow.commit()

    with pytest.raises(RuntimeError):
        _ = uow.rights
    await engine.dispose()


@pytest.mark.asyncio
async def test_acl_uow_rolls_back_and_closes_on_exception() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = SQLAlchemyAccessControlUnitOfWorkFactory(
        async_sessionmaker(engine, expire_on_commit=False)
    )
    uow = factory()

    with pytest.raises(ValueError):
        async with uow:
            raise ValueError("boom")

    with pytest.raises(RuntimeError):
        _ = uow.groups
    await engine.dispose()
