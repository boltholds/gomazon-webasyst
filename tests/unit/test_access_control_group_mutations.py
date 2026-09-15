from gomazon_webasyst.application.access_control import (
    AddGroupMember,
    CreateGroup,
    DeleteGroup,
    RemoveGroupMember,
    ReplaceGroupMembers,
    UpdateGroup,
)
from gomazon_webasyst.application.access_values import GroupId, GroupMembership, GroupTarget
from gomazon_webasyst.application.ports.access_admin_policy import (
    AccessAdministrationAuthorized,
    AccessAdministrationDenied,
)
from gomazon_webasyst.application.ports.access_subjects import (
    AccessSubjectMissing,
    AccessSubjectNotUser,
    AccessSubjectResolved,
)
from gomazon_webasyst.application.ports.groups import GroupDeleteMissing, GroupDeleted as RepoGroupDeleted
from gomazon_webasyst.application.ports.memberships import (
    GroupCountUpdated,
    MembershipAdded,
    MembershipAlreadyAbsent,
    MembershipAlreadyPresent,
    MembershipDeltaApplied,
    MembershipRemoved,
)
from gomazon_webasyst.application.ports.rights import RightsDeleted
from gomazon_webasyst.contracts.access_control import (
    AccessMutationRejected,
    GroupCreate,
    GroupCreated,
    GroupDeleted,
    GroupMembershipAdded,
    GroupMembershipAlreadyAbsent,
    GroupMembershipAlreadyPresent,
    GroupMembershipRemoved,
    GroupMembersReplaced,
    GroupMissing,
    GroupRead,
    GroupResolved,
    GroupUpdate,
    GroupUpdated,
)
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.enums import (
    AccessAdministrationDenyReason,
    AccessMutationRejectReason,
    GroupType,
)


ACTOR = AuthenticatedSubject(id=1, login="admin")
GROUP = GroupRead(
    id=7,
    name="Operators",
    type=GroupType.GROUP,
    member_count=1,
    icon="user",
    sort=0,
    description="",
)


class FakeAdminPolicy:
    def __init__(self, decision):
        self.decision = decision
        self.calls = 0

    async def authorize(self, actor, uow):
        self.calls += 1
        return self.decision


class FakeGroups:
    def __init__(self, *, exists=True):
        self.exists = exists
        self.writes = []

    async def get(self, group_id):
        if self.exists and group_id == GroupId(7):
            return GroupResolved(group=GROUP)
        return GroupMissing(group_id=group_id.value)

    async def create(self, data):
        self.writes.append(("create", data.name))
        return GROUP.model_copy(update={"name": data.name})

    async def update(self, group_id, data):
        self.writes.append(("update", group_id, data.model_dump(exclude_unset=True)))
        if not self.exists:
            return GroupMissing(group_id=group_id.value)
        return GroupResolved(group=GROUP.model_copy(update=data.model_dump(exclude_unset=True)))

    async def delete(self, group_id):
        self.writes.append(("delete", group_id))
        if not self.exists:
            return GroupDeleteMissing(group_id)
        return RepoGroupDeleted(group_id)


class FakeSubjects:
    def __init__(self, results):
        self.results = results

    async def resolve(self, contact_id):
        return self.results.get(contact_id, AccessSubjectMissing(contact_id))


class FakeMemberships:
    def __init__(self, current=()):
        self.current = list(current)
        self.writes = []

    async def list_for_group(self, group_id):
        return tuple(item for item in self.current if item.group_id == group_id)

    async def add(self, membership):
        self.writes.append(("add", membership))
        if membership in self.current:
            return MembershipAlreadyPresent(membership)
        self.current.append(membership)
        return MembershipAdded(membership)

    async def remove(self, membership):
        self.writes.append(("remove", membership))
        if membership not in self.current:
            return MembershipAlreadyAbsent(membership)
        self.current.remove(membership)
        return MembershipRemoved(membership)

    async def apply_delta(self, *, added, removed):
        self.writes.append(("delta", added, removed))
        self.current = [item for item in self.current if item not in removed]
        self.current.extend(item for item in added if item not in self.current)
        return MembershipDeltaApplied(added=added, removed=removed)

    async def recount_group(self, group_id):
        self.writes.append(("recount", group_id))
        count = sum(1 for item in self.current if item.group_id == group_id)
        return GroupCountUpdated(group_id=group_id, count=count)


class FakeRights:
    def __init__(self):
        self.writes = []

    async def delete_all_for_target(self, target):
        self.writes.append(("delete_all", target))
        return RightsDeleted(target=target, deleted_count=2)


class FakeUow:
    def __init__(self, *, exists=True, subjects=None, current=()):
        self.groups = FakeGroups(exists=exists)
        self.subjects = FakeSubjects(subjects or {})
        self.memberships = FakeMemberships(current)
        self.rights = FakeRights()
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    async def commit(self):
        self.commits += 1


class Factory:
    def __init__(self, uow):
        self.uow = uow

    def __call__(self):
        return self.uow


async def test_denied_group_create_does_not_write_or_commit() -> None:
    uow = FakeUow()
    policy = FakeAdminPolicy(
        AccessAdministrationDenied(AccessAdministrationDenyReason.NOT_GLOBAL_ADMIN)
    )

    result = await CreateGroup(Factory(uow), policy)(ACTOR, GroupCreate(name="New"))

    assert isinstance(result, AccessMutationRejected)
    assert result.reason is AccessMutationRejectReason.ACCESS_DENIED
    assert uow.groups.writes == []
    assert uow.commits == 0


async def test_authorized_create_and_update_commit_typed_results() -> None:
    uow = FakeUow()
    policy = FakeAdminPolicy(AccessAdministrationAuthorized())
    factory = Factory(uow)

    created = await CreateGroup(factory, policy)(ACTOR, GroupCreate(name="Engineers"))
    updated = await UpdateGroup(factory, policy)(ACTOR, GroupId(7), GroupUpdate(name="Ops"))

    assert isinstance(created, GroupCreated)
    assert created.group.name == "Engineers"
    assert isinstance(updated, GroupUpdated)
    assert updated.group.name == "Ops"
    assert uow.commits == 2


async def test_delete_group_cleans_memberships_rights_and_group_before_commit() -> None:
    membership = GroupMembership(42, GroupId(7))
    uow = FakeUow(current=(membership,))
    policy = FakeAdminPolicy(AccessAdministrationAuthorized())

    result = await DeleteGroup(Factory(uow), policy)(ACTOR, GroupId(7))

    assert isinstance(result, GroupDeleted)
    assert uow.memberships.writes[0] == ("delta", (), (membership,))
    assert uow.rights.writes == [("delete_all", GroupTarget(GroupId(7)))]
    assert uow.groups.writes[-1] == ("delete", GroupId(7))
    assert uow.commits == 1


async def test_membership_add_validates_contact_and_is_idempotent() -> None:
    membership = GroupMembership(42, GroupId(7))
    uow = FakeUow(
        subjects={42: AccessSubjectResolved(42)},
        current=(membership,),
    )
    policy = FakeAdminPolicy(AccessAdministrationAuthorized())

    result = await AddGroupMember(Factory(uow), policy)(ACTOR, membership)

    assert isinstance(result, GroupMembershipAlreadyPresent)
    assert uow.commits == 0


async def test_membership_rejects_missing_or_non_user_contact_before_write() -> None:
    policy = FakeAdminPolicy(AccessAdministrationAuthorized())
    missing_uow = FakeUow(subjects={42: AccessSubjectMissing(42)})
    non_user_uow = FakeUow(subjects={42: AccessSubjectNotUser(42)})
    membership = GroupMembership(42, GroupId(7))

    missing = await AddGroupMember(Factory(missing_uow), policy)(ACTOR, membership)
    non_user = await AddGroupMember(Factory(non_user_uow), policy)(ACTOR, membership)

    assert isinstance(missing, AccessMutationRejected)
    assert missing.reason is AccessMutationRejectReason.CONTACT_NOT_FOUND
    assert isinstance(non_user, AccessMutationRejected)
    assert non_user.reason is AccessMutationRejectReason.CONTACT_NOT_USER
    assert missing_uow.memberships.writes == []
    assert non_user_uow.memberships.writes == []


async def test_remove_absent_membership_is_explicit_and_does_not_commit() -> None:
    uow = FakeUow(subjects={42: AccessSubjectResolved(42)})
    policy = FakeAdminPolicy(AccessAdministrationAuthorized())

    result = await RemoveGroupMember(Factory(uow), policy)(
        ACTOR,
        GroupMembership(42, GroupId(7)),
    )

    assert isinstance(result, GroupMembershipAlreadyAbsent)
    assert uow.commits == 0


async def test_replace_members_uses_delta_and_preserves_unchanged_membership() -> None:
    current = (
        GroupMembership(42, GroupId(7)),
        GroupMembership(43, GroupId(7)),
    )
    uow = FakeUow(
        subjects={
            42: AccessSubjectResolved(42),
            43: AccessSubjectResolved(43),
            44: AccessSubjectResolved(44),
        },
        current=current,
    )
    policy = FakeAdminPolicy(AccessAdministrationAuthorized())

    result = await ReplaceGroupMembers(Factory(uow), policy)(
        ACTOR,
        GroupId(7),
        (42, 44),
    )

    assert isinstance(result, GroupMembersReplaced)
    assert result.added_contact_ids == (44,)
    assert result.removed_contact_ids == (43,)
    assert uow.memberships.writes[0] == (
        "delta",
        (GroupMembership(44, GroupId(7)),),
        (GroupMembership(43, GroupId(7)),),
    )
    assert uow.memberships.writes[1] == ("recount", GroupId(7))
    assert uow.commits == 1
