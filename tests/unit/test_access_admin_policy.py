import pytest

from gomazon_webasyst.application.access_admin_policy import (
    GlobalAdminAccessAdministrationPolicy,
)
from gomazon_webasyst.application.access_values import AppId, RightValue, UserTarget
from gomazon_webasyst.application.ports.access_admin_policy import (
    AccessAdministrationAuthorized,
    AccessAdministrationDenied,
)
from gomazon_webasyst.application.ports.access_subjects import (
    AccessSubjectMissing,
    AccessSubjectNotUser,
    AccessSubjectResolved,
)
from gomazon_webasyst.application.ports.rights import (
    AppAccessAssignment,
    GlobalAccessAssignment,
    RightsSnapshot,
)
from gomazon_webasyst.application.rights_evaluator import RightsEvaluator
from gomazon_webasyst.compatibility.webasyst.access_control.evaluation import (
    ExactThenLegacyAllFallback,
    WebasystAccessSemantics,
)
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.enums import AccessAdministrationDenyReason


class FakeSubjects:
    def __init__(self, result):
        self.result = result

    async def resolve(self, contact_id):
        return self.result


class FailingSubjects:
    async def resolve(self, contact_id):
        raise RuntimeError("database unavailable")


class FakeMemberships:
    async def list_for_user(self, contact_id):
        return ()


class FakeRights:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    async def load_for_targets(self, targets):
        return self.snapshot


class FakeUow:
    def __init__(self, *, subject_result, snapshot):
        self.subjects = FakeSubjects(subject_result)
        self.memberships = FakeMemberships()
        self.rights = FakeRights(snapshot)


class FailingUow:
    def __init__(self):
        self.subjects = FailingSubjects()
        self.memberships = FakeMemberships()
        self.rights = FakeRights(RightsSnapshot(()))


def policy() -> GlobalAdminAccessAdministrationPolicy:
    return GlobalAdminAccessAdministrationPolicy(
        evaluator=RightsEvaluator(
            app_semantics=WebasystAccessSemantics(),
            fallback_policy=ExactThenLegacyAllFallback(),
        )
    )


@pytest.mark.asyncio
async def test_global_admin_is_authorized() -> None:
    actor = AuthenticatedSubject(id=42, login="admin")
    uow = FakeUow(
        subject_result=AccessSubjectResolved(42),
        snapshot=RightsSnapshot((GlobalAccessAssignment(UserTarget(42), RightValue(1)),)),
    )

    result = await policy().authorize(actor, uow)

    assert isinstance(result, AccessAdministrationAuthorized)


@pytest.mark.asyncio
async def test_application_full_admin_without_global_access_is_denied() -> None:
    actor = AuthenticatedSubject(id=42, login="app-admin")
    uow = FakeUow(
        subject_result=AccessSubjectResolved(42),
        snapshot=RightsSnapshot(
            (AppAccessAssignment(UserTarget(42), AppId("shop"), RightValue(2)),)
        ),
    )

    result = await policy().authorize(actor, uow)

    assert isinstance(result, AccessAdministrationDenied)
    assert result.reason is AccessAdministrationDenyReason.NOT_GLOBAL_ADMIN


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("subject_result", "reason"),
    [
        (AccessSubjectMissing(42), AccessAdministrationDenyReason.ACTOR_NOT_FOUND),
        (AccessSubjectNotUser(42), AccessAdministrationDenyReason.ACTOR_NOT_USER),
    ],
)
async def test_unavailable_actor_is_typed_denial(subject_result, reason) -> None:
    actor = AuthenticatedSubject(id=42, login="actor")
    uow = FakeUow(subject_result=subject_result, snapshot=RightsSnapshot(()))

    result = await policy().authorize(actor, uow)

    assert isinstance(result, AccessAdministrationDenied)
    assert result.reason is reason


@pytest.mark.asyncio
async def test_infrastructure_failure_propagates() -> None:
    actor = AuthenticatedSubject(id=42, login="actor")

    with pytest.raises(RuntimeError, match="database unavailable"):
        await policy().authorize(actor, FailingUow())
