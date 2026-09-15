import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.infrastructure.api_credentials.sqlalchemy.repositories import (
    SQLAlchemyApiTokenRepository,
    SQLAlchemyAuthorizationCodeRepository,
)
from gomazon_webasyst.infrastructure.api_credentials.sqlalchemy.unit_of_work import (
    SQLAlchemyApiCredentialUnitOfWorkFactory,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base


@pytest.mark.asyncio
async def test_api_credential_uow_exposes_repositories_only_while_active_and_commits() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = SQLAlchemyApiCredentialUnitOfWorkFactory(
        async_sessionmaker(engine, expire_on_commit=False)
    )
    uow = factory()

    with pytest.raises(RuntimeError):
        _ = uow.authorization_codes
    with pytest.raises(RuntimeError):
        _ = uow.tokens

    async with uow:
        assert isinstance(uow.authorization_codes, SQLAlchemyAuthorizationCodeRepository)
        assert isinstance(uow.tokens, SQLAlchemyApiTokenRepository)
        await uow.commit()

    with pytest.raises(RuntimeError):
        _ = uow.authorization_codes
    await engine.dispose()


@pytest.mark.asyncio
async def test_api_credential_uow_rolls_back_and_closes_on_exception() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = SQLAlchemyApiCredentialUnitOfWorkFactory(
        async_sessionmaker(engine, expire_on_commit=False)
    )
    uow = factory()

    with pytest.raises(ValueError):
        async with uow:
            raise ValueError("boom")

    with pytest.raises(RuntimeError):
        _ = uow.tokens
    await engine.dispose()
