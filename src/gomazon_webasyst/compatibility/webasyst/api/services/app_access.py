from gomazon_webasyst.application.access_values import AppId, GroupTarget, GuestsTarget, UserTarget
from gomazon_webasyst.application.ports.access_control_uow import AccessControlUnitOfWorkFactory
from gomazon_webasyst.application.ports.access_subjects import AccessSubjectMissing, AccessSubjectNotUser
from gomazon_webasyst.application.ports.api_app_access import (
    ApiAppAccessDecision,
    ApiAppAccessDenied,
    ApiAppAccessGranted,
    ApiAppSubjectUnavailable,
)
from gomazon_webasyst.application.rights_evaluator import RightsEvaluator
from gomazon_webasyst.contracts.access_control import NoAppAccess


class LegacyApiAppAccessService:
    def __init__(
        self,
        uow_factory: AccessControlUnitOfWorkFactory,
        evaluator: RightsEvaluator,
    ) -> None:
        self._uow_factory = uow_factory
        self._evaluator = evaluator

    async def authorize(self, contact_id: int, app_id: AppId) -> ApiAppAccessDecision:
        async with self._uow_factory() as uow:
            subject = await uow.subjects.resolve(contact_id)
            if isinstance(subject, AccessSubjectMissing):
                return ApiAppSubjectUnavailable(contact_id=contact_id, app_id=app_id)
            if isinstance(subject, AccessSubjectNotUser):
                return ApiAppAccessDenied(contact_id=contact_id, app_id=app_id)
            if app_id == AppId("webasyst"):
                return ApiAppAccessGranted(contact_id=contact_id, app_id=app_id)

            memberships = await uow.memberships.list_for_user(contact_id)
            targets = (
                UserTarget(contact_id),
                *(GroupTarget(item.group_id) for item in memberships),
                GuestsTarget(),
            )
            snapshot = await uow.rights.load_for_targets(targets)
            access = self._evaluator.app_access(snapshot, app_id)
            if isinstance(access, NoAppAccess):
                return ApiAppAccessDenied(contact_id=contact_id, app_id=app_id)
            return ApiAppAccessGranted(contact_id=contact_id, app_id=app_id)
