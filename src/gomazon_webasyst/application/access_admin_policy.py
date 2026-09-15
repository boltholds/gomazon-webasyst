from gomazon_webasyst.application.access_control import load_access_snapshot
from gomazon_webasyst.application.ports.access_admin_policy import (
    AccessAdministrationAuthorized,
    AccessAdministrationDecision,
    AccessAdministrationDenied,
)
from gomazon_webasyst.application.ports.access_control_uow import AccessControlUnitOfWork
from gomazon_webasyst.application.rights_evaluator import RightsEvaluator
from gomazon_webasyst.contracts.access_control import AccessReadRejected, GlobalAdminAccess
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.enums import (
    AccessAdministrationDenyReason,
    AccessReadRejectReason,
)


class GlobalAdminAccessAdministrationPolicy:
    def __init__(self, *, evaluator: RightsEvaluator) -> None:
        self._evaluator = evaluator

    async def authorize(
        self,
        actor: AuthenticatedSubject,
        uow: AccessControlUnitOfWork,
    ) -> AccessAdministrationDecision:
        loaded = await load_access_snapshot(uow, actor.id)
        if isinstance(loaded, AccessReadRejected):
            if loaded.reason is AccessReadRejectReason.SUBJECT_NOT_FOUND:
                return AccessAdministrationDenied(
                    reason=AccessAdministrationDenyReason.ACTOR_NOT_FOUND
                )
            return AccessAdministrationDenied(
                reason=AccessAdministrationDenyReason.ACTOR_NOT_USER
            )

        access = self._evaluator.global_admin_access(loaded.snapshot)
        if isinstance(access, GlobalAdminAccess):
            return AccessAdministrationAuthorized()
        return AccessAdministrationDenied(
            reason=AccessAdministrationDenyReason.NOT_GLOBAL_ADMIN
        )
