from gomazon_webasyst.application.access_values import (
    AppId,
    GroupTarget,
    GuestsTarget,
    UserTarget,
)
from gomazon_webasyst.application.ports.access_control_uow import (
    AccessControlUnitOfWorkFactory,
)
from gomazon_webasyst.application.ports.access_subjects import (
    AccessSubjectMissing,
    AccessSubjectNotUser,
)
from gomazon_webasyst.application.ports.oauth_consent_access import (
    OAuthConsentAccessDecision,
    OAuthConsentAccessDenied,
    OAuthConsentAccessGranted,
)
from gomazon_webasyst.application.rights_evaluator import RightsEvaluator
from gomazon_webasyst.contracts.access_control import NoAppAccess
from gomazon_webasyst.contracts.auth import AuthenticatedSubject


class LegacyOAuthConsentAccessService:
    def __init__(
        self,
        uow_factory: AccessControlUnitOfWorkFactory,
        evaluator: RightsEvaluator,
    ) -> None:
        self._uow_factory = uow_factory
        self._evaluator = evaluator

    async def authorize(
        self,
        subject: AuthenticatedSubject,
        app_id: AppId,
    ) -> OAuthConsentAccessDecision:
        async with self._uow_factory() as uow:
            resolved = await uow.subjects.resolve(subject.id)
            if isinstance(resolved, AccessSubjectMissing | AccessSubjectNotUser):
                return OAuthConsentAccessDenied(app_id)

            memberships = await uow.memberships.list_for_user(subject.id)
            targets = (
                UserTarget(subject.id),
                *(GroupTarget(item.group_id) for item in memberships),
                GuestsTarget(),
            )
            snapshot = await uow.rights.load_for_targets(targets)
            access = self._evaluator.app_access(snapshot, app_id)
            if isinstance(access, NoAppAccess):
                return OAuthConsentAccessDenied(app_id)
            return OAuthConsentAccessGranted(app_id)
