from dataclasses import dataclass
from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.ports.api_credentials import (
    ApiTokenRepository,
    AuthorizationCodeRepository,
)
from gomazon_webasyst.compatibility.webasyst.api_credentials import LegacyApiScopeCodec

from .repositories import SQLAlchemyApiTokenRepository, SQLAlchemyAuthorizationCodeRepository


@dataclass(slots=True)
class _InactiveApiCredentialUnitOfWork:
    pass


@dataclass(slots=True)
class _ActiveApiCredentialUnitOfWork:
    session: AsyncSession
    authorization_codes: SQLAlchemyAuthorizationCodeRepository
    tokens: SQLAlchemyApiTokenRepository


_ApiCredentialUnitOfWorkState = _InactiveApiCredentialUnitOfWork | _ActiveApiCredentialUnitOfWork


class SQLAlchemyApiCredentialUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._state: _ApiCredentialUnitOfWorkState = _InactiveApiCredentialUnitOfWork()

    @property
    def authorization_codes(self) -> AuthorizationCodeRepository:
        return self._active().authorization_codes

    @property
    def tokens(self) -> ApiTokenRepository:
        return self._active().tokens

    async def __aenter__(self) -> "SQLAlchemyApiCredentialUnitOfWork":
        if isinstance(self._state, _ActiveApiCredentialUnitOfWork):
            raise RuntimeError("api credential unit of work is already active")
        session = self._session_factory()
        scope_codec = LegacyApiScopeCodec()
        self._state = _ActiveApiCredentialUnitOfWork(
            session=session,
            authorization_codes=SQLAlchemyAuthorizationCodeRepository(session, scope_codec),
            tokens=SQLAlchemyApiTokenRepository(session, scope_codec),
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        active = self._active()
        try:
            if exc_type is not None:
                await active.session.rollback()
        finally:
            await active.session.close()
            self._state = _InactiveApiCredentialUnitOfWork()

    async def commit(self) -> None:
        await self._active().session.commit()

    async def rollback(self) -> None:
        await self._active().session.rollback()

    def _active(self) -> _ActiveApiCredentialUnitOfWork:
        if isinstance(self._state, _InactiveApiCredentialUnitOfWork):
            raise RuntimeError("api credential unit of work is not active")
        return self._state


class SQLAlchemyApiCredentialUnitOfWorkFactory:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    def __call__(self) -> SQLAlchemyApiCredentialUnitOfWork:
        return SQLAlchemyApiCredentialUnitOfWork(self._session_factory)
