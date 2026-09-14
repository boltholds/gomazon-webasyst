from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeAlias
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.auth_values import AuthSessionKey
from gomazon_webasyst.contracts.auth import (
    AuthSessionRegistration,
    RegistryActive,
    RegistryAlreadyMissing,
    RegistryCheckResult,
    RegistryMissing,
    RegistryRevocationResult,
    RegistryRevoked,
    RegistryTouchMissing,
    RegistryTouchResult,
    RegistryTouched,
    RegistryWritten,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import WaContactAuthRow


@dataclass(frozen=True, slots=True)
class _AuthRowFound:
    row: WaContactAuthRow


@dataclass(frozen=True, slots=True)
class _AuthRowMissing:
    pass


_AuthRowLookup: TypeAlias = _AuthRowFound | _AuthRowMissing


class SQLAlchemyAuthSessionRegistry:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._session_factory = session_factory
        self._clock = clock

    async def register(self, registration: AuthSessionRegistration) -> RegistryWritten:
        now = self._clock()
        async with self._session_factory() as session:
            row_result = await self._by_session_id(session, registration.key.session_id.value)
            if isinstance(row_result, _AuthRowMissing):
                session.add(
                    WaContactAuthRow(
                        contact_id=registration.key.contact_id,
                        session_id=registration.key.session_id.value,
                        token=registration.credential_token,
                        login_datetime=now,
                        user_agent=registration.user_agent,
                    )
                )
            else:
                row = row_result.row
                row.contact_id = registration.key.contact_id
                row.token = registration.credential_token
                row.user_agent = registration.user_agent
                row.last_datetime = now
            await session.commit()
        return RegistryWritten()

    async def check(self, key: AuthSessionKey) -> RegistryCheckResult:
        async with self._session_factory() as session:
            row_result = await self._by_key(session, key)
        return RegistryActive() if isinstance(row_result, _AuthRowFound) else RegistryMissing()

    async def touch(self, key: AuthSessionKey) -> RegistryTouchResult:
        async with self._session_factory() as session:
            row_result = await self._by_key(session, key)
            if isinstance(row_result, _AuthRowMissing):
                return RegistryTouchMissing()
            row_result.row.last_datetime = self._clock()
            await session.commit()
        return RegistryTouched()

    async def revoke(self, key: AuthSessionKey) -> RegistryRevocationResult:
        async with self._session_factory() as session:
            row_result = await self._by_key(session, key)
            if isinstance(row_result, _AuthRowMissing):
                return RegistryAlreadyMissing()
            await session.delete(row_result.row)
            await session.commit()
        return RegistryRevoked()

    @staticmethod
    async def _by_session_id(session: AsyncSession, session_id: str) -> "_AuthRowLookup":
        statement = select(WaContactAuthRow).where(WaContactAuthRow.session_id == session_id).limit(1)
        row = (await session.execute(statement)).scalars().first()
        return _AuthRowMissing() if row is None else _AuthRowFound(row=row)

    @staticmethod
    async def _by_key(session: AsyncSession, key: AuthSessionKey) -> "_AuthRowLookup":
        statement = (
            select(WaContactAuthRow)
            .where(
                WaContactAuthRow.contact_id == key.contact_id,
                WaContactAuthRow.session_id == key.session_id.value,
            )
            .limit(1)
        )
        row = (await session.execute(statement)).scalars().first()
        return _AuthRowMissing() if row is None else _AuthRowFound(row=row)
