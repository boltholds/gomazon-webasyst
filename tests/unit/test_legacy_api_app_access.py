import pytest

from gomazon_webasyst.application.access_values import AppId, UserTarget
from gomazon_webasyst.application.ports.access_subjects import (
    AccessSubjectMissing,
    AccessSubjectNotUser,
    AccessSubjectResolved,
)
from gomazon_webasyst.application.ports.api_app_access import (
    ApiAppAccessDenied,
    ApiAppAccessGranted,
    ApiAppSubjectUnavailable,
)
from gomazon_webasyst.compatibility.webasyst.api.services.app_access import LegacyApiAppAccessService
from gomazon_webasyst.compatibility.webasyst.access_control.evaluation import (
    ExactThenLegacyAllFallback,
    WebasystAccessSemantics,
)
from gomazon_webasyst.application.rights_evaluator import RightsEvaluator
from gomazon_webasyst.application.access_values import RightValue
from gomazon_webasyst.application.ports.rights import AppAccessAssignment, RightsSnapshot


class Subjects:
    def __init__(self, result):
        self.result = result
        self.calls = []
    async def resolve(self, contact_id):
        self.calls.append(contact_id)
        return self.result


class Memberships:
    async def list_for_user(self, contact_id):
        return ()


class Rights:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.calls = []
    async def load_for_targets(self, targets):
        self.calls.append(targets)
        return self.snapshot


class Uow:
    def __init__(self, subject_result, snapshot=RightsSnapshot(assignments=())):
        self.subjects = Subjects(subject_result)
        self.memberships = Memberships()
        self.rights = Rights(snapshot)
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_value, traceback):
        return None


def evaluator():
    return RightsEvaluator(
        app_semantics=WebasystAccessSemantics(),
        fallback_policy=ExactThenLegacyAllFallback(),
    )


@pytest.mark.asyncio
async def test_missing_subject_is_unavailable() -> None:
    service = LegacyApiAppAccessService(lambda: Uow(AccessSubjectMissing(42)), evaluator())
    result = await service.authorize(42, AppId("shop"))
    assert isinstance(result, ApiAppSubjectUnavailable)


@pytest.mark.asyncio
async def test_non_user_is_denied() -> None:
    service = LegacyApiAppAccessService(lambda: Uow(AccessSubjectNotUser(42)), evaluator())
    result = await service.authorize(42, AppId("shop"))
    assert isinstance(result, ApiAppAccessDenied)


@pytest.mark.asyncio
async def test_webasyst_user_is_granted_without_rights_lookup() -> None:
    uow = Uow(AccessSubjectResolved(42))
    service = LegacyApiAppAccessService(lambda: uow, evaluator())
    result = await service.authorize(42, AppId("webasyst"))
    assert isinstance(result, ApiAppAccessGranted)
    assert uow.rights.calls == []


@pytest.mark.asyncio
async def test_normal_app_requires_positive_backend_access() -> None:
    denied = LegacyApiAppAccessService(
        lambda: Uow(AccessSubjectResolved(42)),
        evaluator(),
    )
    granted = LegacyApiAppAccessService(
        lambda: Uow(
            AccessSubjectResolved(42),
            RightsSnapshot(
                assignments=(
                    AppAccessAssignment(
                        target=UserTarget(42),
                        app_id=AppId("shop"),
                        value=RightValue(1),
                    ),
                )
            ),
        ),
        evaluator(),
    )
    assert isinstance(await denied.authorize(42, AppId("shop")), ApiAppAccessDenied)
    assert isinstance(await granted.authorize(42, AppId("shop")), ApiAppAccessGranted)
