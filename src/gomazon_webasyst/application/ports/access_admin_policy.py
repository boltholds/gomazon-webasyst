from dataclasses import dataclass
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.ports.access_control_uow import AccessControlUnitOfWork
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.enums import AccessAdministrationDenyReason


@dataclass(slots=True, frozen=True)
class AccessAdministrationAuthorized:
    pass


@dataclass(slots=True, frozen=True)
class AccessAdministrationDenied:
    reason: AccessAdministrationDenyReason


AccessAdministrationDecision: TypeAlias = (
    AccessAdministrationAuthorized | AccessAdministrationDenied
)


class AccessAdministrationPolicy(Protocol):
    async def authorize(
        self,
        actor: AuthenticatedSubject,
        uow: AccessControlUnitOfWork,
    ) -> AccessAdministrationDecision: ...
