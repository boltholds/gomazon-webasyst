from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from gomazon_webasyst.composition.settings import Settings

from .unit_of_work import SQLAlchemyUnitOfWorkFactory


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(settings.database_url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine):
    return async_sessionmaker(engine, expire_on_commit=False)


def create_uow_factory(engine: AsyncEngine) -> SQLAlchemyUnitOfWorkFactory:
    return SQLAlchemyUnitOfWorkFactory(create_session_factory(engine))
