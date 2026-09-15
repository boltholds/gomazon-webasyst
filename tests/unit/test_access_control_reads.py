from gomazon_webasyst.application.access_control import (
    GetAppAccess,
    GetEffectiveRight,
    GetGroup,
    GetRightsSnapshot,
    ListGroupMembers,
    ListGroups,
    ListUserGroups,
)
from gomazon_webasyst.application.access_values import (
    AppId,
    GroupId,
    GroupMembership,
    GroupTarget,
    GuestsTarget,
    PermissionKey,
    RightName,
    RightValue,
    UserTarget,
)
from gomazon_webasyst.application.ports.access_subjects import (
    AccessSubjectMissing,
    AccessSubjectNotUser,
    AccessSubjectResolved,
)
from gomazon_webasyst.application.ports.rights import (
    AppAccessAssignment,
    NamedRightAssignment,
    RightsSnapshot,
)
from gomazon_webasyst.application.rights_evaluator import RightsEvaluator
from gomazon_webasyst.compatibility.webasyst.access_control.evaluation import (
    ExactThenLegacyAllFallback,
    WebasystAccessSemantics,
)
from gomazon_webasyst.contracts.access_control import (
    AccessReadRejected,
    AppAccessResolved,
    EffectiveRightResolved,
    FiniteRight,
    FiniteRightsSnapshot,
    GroupMembersResolved,
    GroupMissing,
    GroupRead,
    GroupResolved,
    RightsSnapshotResolved,
    UserGroupsResolved,
)
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.enums import AccessReadRejectReason, GroupType


GROUP = GroupRead(
    id=7,
    name="Operators",
    type=GroupType.GROUP,
    member_count=1,
    icon="user",
    sort=0,
    description="",
)


class FakeGroups:
    async def get(self, group_id):
        if group_id == GroupId(7):
            return GroupResolved(group=GROUP)
        return GroupMissing(group_id=group_id.value)

    async def list(self):
        return (GROUP,)


class FakeMemberships:
    async def list_for_user(self, contact_id):
        return (GroupMembership(contact_id, GroupId(7)),)

    async def list_for_group(self, group_id):
        return (GroupMembership(42, group_id),)


class FakeRights:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.loaded_targets = ()

    async def load_for_targets(self, targets):
        self.loaded_targets = targets
        return self.snapshot


class FakeSubjects:
    def __init__(self, result):
        self.result = result

    async def resolve(self, contact_id):
        return self.result


class FakeUow:
    def __init__(self, *, subject_result, snapshot):
        self.groups = FakeGroups()
        self.memberships = FakeMemberships()
        self.rights = FakeRights(snapshot)
        self.subjects = FakeSubjects(subject_result)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None


class Factory:
    def __init__(self, uow):
        self.uow = uow

    def __call__(self):
        return self.uow


def evaluator():
    return RightsEvaluator(
        app_semantics=WebasystAccessSemantics(),
        fallback_policy=ExactThenLegacyAllFallback(),
    )


async def test_group_and_membership_reads_use_typed_contracts() -> None:
    uow = FakeUow(subject_result=AccessSubjectResolved(42), snapshot=RightsSnapshot(()))
    factory = Factory(uow)

    assert isinstance(await GetGroup(factory)(GroupId(7)), GroupResolved)
    assert await ListGroups(factory)() == (GROUP,)

    user_groups = await ListUserGroups(factory)(42)
    assert isinstance(user_groups, UserGroupsResolved)
    assert user_groups.groups == (GROUP,)

    members = await ListGroupMembers(factory)(GroupId(7))
    assert isinstance(members, GroupMembersResolved)
    assert members.contact_ids == (42,)


async def test_effective_read_collects_user_groups_and_guests_before_evaluation() -> None:
    subject = AuthenticatedSubject(id=42, login="admin")
    key = PermissionKey(AppId("shop"), RightName("orders.edit"))
    snapshot = RightsSnapshot(
        (
            AppAccessAssignment(UserTarget(42), AppId("shop"), RightValue(1)),
            NamedRightAssignment(GroupTarget(GroupId(7)), key, RightValue(4)),
        )
    )
    uow = FakeUow(subject_result=AccessSubjectResolved(42), snapshot=snapshot)
    factory = Factory(uow)

    result = await GetEffectiveRight(factory, evaluator())(subject, key)

    assert isinstance(result, EffectiveRightResolved)
    assert isinstance(result.right, FiniteRight)
    assert result.right.value == 4
    assert uow.rights.loaded_targets == (
        UserTarget(42),
        GroupTarget(GroupId(7)),
        GuestsTarget(),
    )


async def test_app_access_and_rights_snapshot_are_explicit_results() -> None:
    subject = AuthenticatedSubject(id=42, login="admin")
    snapshot = RightsSnapshot(
        (AppAccessAssignment(UserTarget(42), AppId("shop"), RightValue(1)),)
    )
    factory = Factory(FakeUow(subject_result=AccessSubjectResolved(42), snapshot=snapshot))

    access = await GetAppAccess(factory, evaluator())(subject, AppId("shop"))
    rights = await GetRightsSnapshot(factory, evaluator())(subject, AppId("shop"))

    assert isinstance(access, AppAccessResolved)
    assert isinstance(rights, RightsSnapshotResolved)
    assert isinstance(rights.snapshot, FiniteRightsSnapshot)


async def test_missing_and_non_user_subjects_are_typed_rejections() -> None:
    subject = AuthenticatedSubject(id=42, login="admin")
    key = PermissionKey(AppId("shop"), RightName("orders.edit"))

    missing = await GetEffectiveRight(
        Factory(FakeUow(subject_result=AccessSubjectMissing(42), snapshot=RightsSnapshot(()))),
        evaluator(),
    )(subject, key)
    not_user = await GetAppAccess(
        Factory(FakeUow(subject_result=AccessSubjectNotUser(42), snapshot=RightsSnapshot(()))),
        evaluator(),
    )(subject, AppId("shop"))

    assert isinstance(missing, AccessReadRejected)
    assert missing.reason is AccessReadRejectReason.SUBJECT_NOT_FOUND
    assert isinstance(not_user, AccessReadRejected)
    assert not_user.reason is AccessReadRejectReason.SUBJECT_NOT_USER
