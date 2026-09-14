from collections.abc import Callable
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


class SQLAlchemyAuthSessionRegistry:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._clock = clock or datetime.now

    async def register(self, registration: AuthSessionRegistration) -> RegistryWritten:
        now = self._clock()
        async with self._session_factory() as session:
            row = await self._by_session_id(session, registration.key.session_id.value)
            if row is None:
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
                row.contact_id = registration.key.contact_id
                row.token = registration.credential_token
                row.user_agent = registration.user_agent
                row.last_datetime = now
            await session.commit()
        return RegistryWritten()

    async def check(self, key: AuthSessionKey) -> RegistryCheckResult:
        async with self._session_factory() as session:
            row = await self._by_key(session, key)
        return RegistryActive() if row is not None else RegistryMissing()

    async def touch(self, key: AuthSessionKey) -> RegistryTouchResult:
        async with self._session_factory() as session:
            row = await self._by_key(session, key)
            if row is None:
                return RegistryTouchMissing()
            row.last_datetime = self._clock()
            await session.commit()
        return RegistryTouched()

    async def revoke(self, key: AuthSessionKey) -> RegistryRevocationResult:
        async with self._session_factory() as session:
            row = await self._by_key(session, key)
            if row is None:
                return RegistryAlreadyMissing()
            await session.delete(row)
            await session.commit()
        return RegistryRevoked()

    @staticmethod
    async def _by_session_id(session: AsyncSession, session_id: str) -> WaContactAuthRow | None:
        statement = select(WaContactAuthRow).where(WaContactAuthRow.session_id == session_id).limit(1)
        return (await session.execute(statement)).scalars().first()

    @staticmethod
    async def _by_key(session: AsyncSession, key: AuthSessionKey) -> WaContactAuthRow | None:
        statement = (
            select(WaContactAuthRow)
            .where(
                WaContactAuthRow.contact_id == key.contact_id,
                WaContactAuthRow.session_id == key.session_id.value,
            )
            .limit(1)
        )
        return (await session.execute(statement)).scalars().first()
