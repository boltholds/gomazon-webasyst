from dataclasses import dataclass
from types import TracebackType
from typing import TypeAlias

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .repositories import SQLAlchemyContactRepository


@dataclass(slots=True)
class _InactiveUnitOfWork:
    pass


@dataclass(slots=True)
class _ActiveUnitOfWork:
    session: AsyncSession
    contacts: SQLAlchemyContactRepository


_UnitOfWorkState: TypeAlias = _InactiveUnitOfWork | _ActiveUnitOfWork


class SQLAlchemyUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._state: _UnitOfWorkState = _InactiveUnitOfWork()

    @property
    def contacts(self) -> SQLAlchemyContactRepository:
        return self._active().contacts

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        session = self._session_factory()
        self._state = _ActiveUnitOfWork(
            session=session,
            contacts=SQLAlchemyContactRepository(session),
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        active = self._active()
        try:
            if exc is not None:
                await active.session.rollback()
        finally:
            await active.session.close()
            self._state = _InactiveUnitOfWork()

    async def commit(self) -> None:
        await self._active().session.commit()

    async def rollback(self) -> None:
        await self._active().session.rollback()

    def _active(self) -> _ActiveUnitOfWork:
        if isinstance(self._state, _InactiveUnitOfWork):
            raise RuntimeError("unit of work is not active")
        return self._state


class SQLAlchemyUnitOfWorkFactory:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    def __call__(self) -> SQLAlchemyUnitOfWork:
        return SQLAlchemyUnitOfWork(self._session_factory)
