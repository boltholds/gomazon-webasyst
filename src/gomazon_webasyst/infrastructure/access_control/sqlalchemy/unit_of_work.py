from dataclasses import dataclass
from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.ports.access_subjects import AccessSubjectStore
from gomazon_webasyst.application.ports.groups import GroupRepository
from gomazon_webasyst.application.ports.memberships import MembershipRepository
from gomazon_webasyst.application.ports.rights import RightsRepository
from gomazon_webasyst.compatibility.webasyst.access_control.principals import WebasystPrincipalCodec

from .groups import SQLAlchemyGroupRepository
from .memberships import SQLAlchemyMembershipRepository
from .rights import SQLAlchemyRightsRepository
from .subjects import SQLAlchemyAccessSubjectStore


@dataclass(slots=True)
class _InactiveAccessControlUnitOfWork:
    pass


@dataclass(slots=True)
class _ActiveAccessControlUnitOfWork:
    session: AsyncSession
    groups: SQLAlchemyGroupRepository
    memberships: SQLAlchemyMembershipRepository
    rights: SQLAlchemyRightsRepository
    subjects: SQLAlchemyAccessSubjectStore


_AccessControlUnitOfWorkState = _InactiveAccessControlUnitOfWork | _ActiveAccessControlUnitOfWork


class SQLAlchemyAccessControlUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._state: _AccessControlUnitOfWorkState = _InactiveAccessControlUnitOfWork()

    @property
    def groups(self) -> GroupRepository:
        return self._active().groups

    @property
    def memberships(self) -> MembershipRepository:
        return self._active().memberships

    @property
    def rights(self) -> RightsRepository:
        return self._active().rights

    @property
    def subjects(self) -> AccessSubjectStore:
        return self._active().subjects

    async def __aenter__(self) -> "SQLAlchemyAccessControlUnitOfWork":
        if isinstance(self._state, _ActiveAccessControlUnitOfWork):
            raise RuntimeError("access control unit of work is already active")
        session = self._session_factory()
        self._state = _ActiveAccessControlUnitOfWork(
            session=session,
            groups=SQLAlchemyGroupRepository(session),
            memberships=SQLAlchemyMembershipRepository(session),
            rights=SQLAlchemyRightsRepository(
                session,
                principal_codec=WebasystPrincipalCodec(),
            ),
            subjects=SQLAlchemyAccessSubjectStore(session),
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
            self._state = _InactiveAccessControlUnitOfWork()

    async def commit(self) -> None:
        await self._active().session.commit()

    async def rollback(self) -> None:
        await self._active().session.rollback()

    def _active(self) -> _ActiveAccessControlUnitOfWork:
        if isinstance(self._state, _InactiveAccessControlUnitOfWork):
            raise RuntimeError("access control unit of work is not active")
        return self._state


class SQLAlchemyAccessControlUnitOfWorkFactory:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    def __call__(self) -> SQLAlchemyAccessControlUnitOfWork:
        return SQLAlchemyAccessControlUnitOfWork(self._session_factory)
