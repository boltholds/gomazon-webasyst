from types import TracebackType
from typing import Callable, Protocol

from gomazon_webasyst.application.ports.access_subjects import AccessSubjectStore
from gomazon_webasyst.application.ports.groups import GroupRepository
from gomazon_webasyst.application.ports.memberships import MembershipRepository
from gomazon_webasyst.application.ports.rights import RightsRepository


class AccessControlUnitOfWork(Protocol):
    @property
    def groups(self) -> GroupRepository: ...

    @property
    def memberships(self) -> MembershipRepository: ...

    @property
    def rights(self) -> RightsRepository: ...

    @property
    def subjects(self) -> AccessSubjectStore: ...

    async def __aenter__(self) -> "AccessControlUnitOfWork": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


AccessControlUnitOfWorkFactory = Callable[[], AccessControlUnitOfWork]
