from dataclasses import dataclass

from gomazon_webasyst.application.access_values import (
    AppId,
    GroupId,
    GroupMembership,
    GroupTarget,
    GuestsTarget,
    PermissionKey,
    UserTarget,
)
from gomazon_webasyst.application.ports.access_admin_policy import (
    AccessAdministrationDenied,
    AccessAdministrationPolicy,
)
from gomazon_webasyst.application.ports.access_control_uow import (
    AccessControlUnitOfWork,
    AccessControlUnitOfWorkFactory,
)
from gomazon_webasyst.application.ports.access_subjects import (
    AccessSubjectMissing,
    AccessSubjectNotUser,
)
from gomazon_webasyst.application.ports.groups import GroupDeleteMissing
from gomazon_webasyst.application.ports.memberships import (
    MembershipAdded,
    MembershipAlreadyAbsent,
    MembershipAlreadyPresent,
    MembershipRemoved,
)
from gomazon_webasyst.application.ports.rights import RightsSnapshot
from gomazon_webasyst.application.rights_evaluator import RightsEvaluator
from gomazon_webasyst.contracts.access_control import (
    AccessMutationRejected,
    AccessReadRejected,
    AppAccessResolved,
    AppAccessResult,
    EffectiveRightResolved,
    EffectiveRightResult,
    GroupCreate,
    GroupCreated,
    GroupDeleted,
    GroupMembersReplaced,
    GroupMembersResolved,
    GroupMembersResult,
    GroupMembershipAdded,
    GroupMembershipAlreadyAbsent,
    GroupMembershipAlreadyPresent,
    GroupMembershipRemoved,
    GroupMissing,
    GroupRead,
    GroupResolved,
    GroupResolution,
    GroupUpdate,
    GroupUpdated,
    RightsSnapshotQueryResult,
    RightsSnapshotResolved,
    UserGroupsResolved,
    UserGroupsResult,
)
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.enums import (
    AccessMutationRejectReason,
    AccessReadRejectReason,
)


@dataclass(slots=True, frozen=True)
class AccessSnapshotLoaded:
    snapshot: RightsSnapshot


AccessSnapshotLoadResult = AccessSnapshotLoaded | AccessReadRejected


async def load_access_snapshot(
    uow: AccessControlUnitOfWork,
    contact_id: int,
) -> AccessSnapshotLoadResult:
    subject = await uow.subjects.resolve(contact_id)
    if isinstance(subject, AccessSubjectMissing):
        return AccessReadRejected(reason=AccessReadRejectReason.SUBJECT_NOT_FOUND)
    if isinstance(subject, AccessSubjectNotUser):
        return AccessReadRejected(reason=AccessReadRejectReason.SUBJECT_NOT_USER)

    memberships = await uow.memberships.list_for_user(contact_id)
    targets = (
        UserTarget(contact_id),
        *(GroupTarget(membership.group_id) for membership in memberships),
        GuestsTarget(),
    )
    return AccessSnapshotLoaded(snapshot=await uow.rights.load_for_targets(targets))


async def _authorize_mutation(
    policy: AccessAdministrationPolicy,
    actor: AuthenticatedSubject,
    uow: AccessControlUnitOfWork,
) -> AccessMutationRejected | None:
    decision = await policy.authorize(actor, uow)
    if isinstance(decision, AccessAdministrationDenied):
        return AccessMutationRejected(reason=AccessMutationRejectReason.ACCESS_DENIED)
    return None


class GetGroup:
    def __init__(self, uow_factory: AccessControlUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def __call__(self, group_id: GroupId) -> GroupResolution:
        async with self._uow_factory() as uow:
            return await uow.groups.get(group_id)


class ListGroups:
    def __init__(self, uow_factory: AccessControlUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def __call__(self) -> tuple[GroupRead, ...]:
        async with self._uow_factory() as uow:
            return await uow.groups.list()


class ListUserGroups:
    def __init__(self, uow_factory: AccessControlUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def __call__(self, contact_id: int) -> UserGroupsResult:
        async with self._uow_factory() as uow:
            subject = await uow.subjects.resolve(contact_id)
            if isinstance(subject, AccessSubjectMissing):
                return AccessReadRejected(reason=AccessReadRejectReason.SUBJECT_NOT_FOUND)
            if isinstance(subject, AccessSubjectNotUser):
                return AccessReadRejected(reason=AccessReadRejectReason.SUBJECT_NOT_USER)

            memberships = await uow.memberships.list_for_user(contact_id)
            groups: list[GroupRead] = []
            for membership in memberships:
                resolved = await uow.groups.get(membership.group_id)
                if isinstance(resolved, GroupResolved):
                    groups.append(resolved.group)
            return UserGroupsResolved(groups=tuple(groups))


class ListGroupMembers:
    def __init__(self, uow_factory: AccessControlUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def __call__(self, group_id: GroupId) -> GroupMembersResult:
        async with self._uow_factory() as uow:
            resolved = await uow.groups.get(group_id)
            if isinstance(resolved, GroupMissing):
                return AccessReadRejected(reason=AccessReadRejectReason.GROUP_NOT_FOUND)
            memberships = await uow.memberships.list_for_group(group_id)
            return GroupMembersResolved(
                contact_ids=tuple(membership.contact_id for membership in memberships)
            )


class GetEffectiveRight:
    def __init__(
        self,
        uow_factory: AccessControlUnitOfWorkFactory,
        evaluator: RightsEvaluator,
    ) -> None:
        self._uow_factory = uow_factory
        self._evaluator = evaluator

    async def __call__(
        self,
        subject: AuthenticatedSubject,
        key: PermissionKey,
    ) -> EffectiveRightResult:
        async with self._uow_factory() as uow:
            loaded = await load_access_snapshot(uow, subject.id)
            if isinstance(loaded, AccessReadRejected):
                return loaded
            return EffectiveRightResolved(
                right=self._evaluator.effective_right(loaded.snapshot, key)
            )


class GetAppAccess:
    def __init__(
        self,
        uow_factory: AccessControlUnitOfWorkFactory,
        evaluator: RightsEvaluator,
    ) -> None:
        self._uow_factory = uow_factory
        self._evaluator = evaluator

    async def __call__(
        self,
        subject: AuthenticatedSubject,
        app_id: AppId,
    ) -> AppAccessResult:
        async with self._uow_factory() as uow:
            loaded = await load_access_snapshot(uow, subject.id)
            if isinstance(loaded, AccessReadRejected):
                return loaded
            return AppAccessResolved(
                access=self._evaluator.app_access(loaded.snapshot, app_id)
            )


class GetRightsSnapshot:
    def __init__(
        self,
        uow_factory: AccessControlUnitOfWorkFactory,
        evaluator: RightsEvaluator,
    ) -> None:
        self._uow_factory = uow_factory
        self._evaluator = evaluator

    async def __call__(
        self,
        subject: AuthenticatedSubject,
        app_id: AppId,
    ) -> RightsSnapshotQueryResult:
        async with self._uow_factory() as uow:
            loaded = await load_access_snapshot(uow, subject.id)
            if isinstance(loaded, AccessReadRejected):
                return loaded
            snapshot = self._evaluator.rights_snapshot(loaded.snapshot, app_id)
            return RightsSnapshotResolved(snapshot=snapshot)


class CreateGroup:
    def __init__(
        self,
        uow_factory: AccessControlUnitOfWorkFactory,
        admin_policy: AccessAdministrationPolicy,
    ) -> None:
        self._uow_factory = uow_factory
        self._admin_policy = admin_policy

    async def __call__(
        self,
        actor: AuthenticatedSubject,
        data: GroupCreate,
    ) -> GroupCreated | AccessMutationRejected:
        async with self._uow_factory() as uow:
            denied = await _authorize_mutation(self._admin_policy, actor, uow)
            if denied is not None:
                return denied
            group = await uow.groups.create(data)
            await uow.commit()
            return GroupCreated(group=group)


class UpdateGroup:
    def __init__(
        self,
        uow_factory: AccessControlUnitOfWorkFactory,
        admin_policy: AccessAdministrationPolicy,
    ) -> None:
        self._uow_factory = uow_factory
        self._admin_policy = admin_policy

    async def __call__(
        self,
        actor: AuthenticatedSubject,
        group_id: GroupId,
        data: GroupUpdate,
    ) -> GroupUpdated | AccessMutationRejected:
        async with self._uow_factory() as uow:
            denied = await _authorize_mutation(self._admin_policy, actor, uow)
            if denied is not None:
                return denied
            updated = await uow.groups.update(group_id, data)
            if isinstance(updated, GroupMissing):
                return AccessMutationRejected(reason=AccessMutationRejectReason.GROUP_NOT_FOUND)
            await uow.commit()
            return GroupUpdated(group=updated.group)


class DeleteGroup:
    def __init__(
        self,
        uow_factory: AccessControlUnitOfWorkFactory,
        admin_policy: AccessAdministrationPolicy,
    ) -> None:
        self._uow_factory = uow_factory
        self._admin_policy = admin_policy

    async def __call__(
        self,
        actor: AuthenticatedSubject,
        group_id: GroupId,
    ) -> GroupDeleted | AccessMutationRejected:
        async with self._uow_factory() as uow:
            denied = await _authorize_mutation(self._admin_policy, actor, uow)
            if denied is not None:
                return denied
            resolved = await uow.groups.get(group_id)
            if isinstance(resolved, GroupMissing):
                return AccessMutationRejected(reason=AccessMutationRejectReason.GROUP_NOT_FOUND)

            memberships = await uow.memberships.list_for_group(group_id)
            if memberships:
                await uow.memberships.apply_delta(added=(), removed=memberships)
            await uow.rights.delete_all_for_target(GroupTarget(group_id))
            deleted = await uow.groups.delete(group_id)
            if isinstance(deleted, GroupDeleteMissing):
                return AccessMutationRejected(reason=AccessMutationRejectReason.GROUP_NOT_FOUND)
            await uow.commit()
            return GroupDeleted(group_id=group_id.value)


class AddGroupMember:
    def __init__(
        self,
        uow_factory: AccessControlUnitOfWorkFactory,
        admin_policy: AccessAdministrationPolicy,
    ) -> None:
        self._uow_factory = uow_factory
        self._admin_policy = admin_policy

    async def __call__(
        self,
        actor: AuthenticatedSubject,
        membership: GroupMembership,
    ) -> GroupMembershipAdded | GroupMembershipAlreadyPresent | AccessMutationRejected:
        async with self._uow_factory() as uow:
            denied = await _authorize_mutation(self._admin_policy, actor, uow)
            if denied is not None:
                return denied
            group = await uow.groups.get(membership.group_id)
            if isinstance(group, GroupMissing):
                return AccessMutationRejected(reason=AccessMutationRejectReason.GROUP_NOT_FOUND)
            subject = await uow.subjects.resolve(membership.contact_id)
            if isinstance(subject, AccessSubjectMissing):
                return AccessMutationRejected(reason=AccessMutationRejectReason.CONTACT_NOT_FOUND)
            if isinstance(subject, AccessSubjectNotUser):
                return AccessMutationRejected(reason=AccessMutationRejectReason.CONTACT_NOT_USER)

            added = await uow.memberships.add(membership)
            if isinstance(added, MembershipAlreadyPresent):
                return GroupMembershipAlreadyPresent(
                    contact_id=membership.contact_id,
                    group_id=membership.group_id.value,
                )
            assert isinstance(added, MembershipAdded)
            count = await uow.memberships.recount_group(membership.group_id)
            await uow.commit()
            return GroupMembershipAdded(
                contact_id=membership.contact_id,
                group_id=membership.group_id.value,
                member_count=count.count,
            )


class RemoveGroupMember:
    def __init__(
        self,
        uow_factory: AccessControlUnitOfWorkFactory,
        admin_policy: AccessAdministrationPolicy,
    ) -> None:
        self._uow_factory = uow_factory
        self._admin_policy = admin_policy

    async def __call__(
        self,
        actor: AuthenticatedSubject,
        membership: GroupMembership,
    ) -> GroupMembershipRemoved | GroupMembershipAlreadyAbsent | AccessMutationRejected:
        async with self._uow_factory() as uow:
            denied = await _authorize_mutation(self._admin_policy, actor, uow)
            if denied is not None:
                return denied
            group = await uow.groups.get(membership.group_id)
            if isinstance(group, GroupMissing):
                return AccessMutationRejected(reason=AccessMutationRejectReason.GROUP_NOT_FOUND)

            removed = await uow.memberships.remove(membership)
            if isinstance(removed, MembershipAlreadyAbsent):
                return GroupMembershipAlreadyAbsent(
                    contact_id=membership.contact_id,
                    group_id=membership.group_id.value,
                )
            assert isinstance(removed, MembershipRemoved)
            count = await uow.memberships.recount_group(membership.group_id)
            await uow.commit()
            return GroupMembershipRemoved(
                contact_id=membership.contact_id,
                group_id=membership.group_id.value,
                member_count=count.count,
            )


class ReplaceGroupMembers:
    def __init__(
        self,
        uow_factory: AccessControlUnitOfWorkFactory,
        admin_policy: AccessAdministrationPolicy,
    ) -> None:
        self._uow_factory = uow_factory
        self._admin_policy = admin_policy

    async def __call__(
        self,
        actor: AuthenticatedSubject,
        group_id: GroupId,
        contact_ids: tuple[int, ...],
    ) -> GroupMembersReplaced | AccessMutationRejected:
        async with self._uow_factory() as uow:
            denied = await _authorize_mutation(self._admin_policy, actor, uow)
            if denied is not None:
                return denied
            group = await uow.groups.get(group_id)
            if isinstance(group, GroupMissing):
                return AccessMutationRejected(reason=AccessMutationRejectReason.GROUP_NOT_FOUND)

            requested = tuple(dict.fromkeys(contact_ids))
            for contact_id in requested:
                subject = await uow.subjects.resolve(contact_id)
                if isinstance(subject, AccessSubjectMissing):
                    return AccessMutationRejected(reason=AccessMutationRejectReason.CONTACT_NOT_FOUND)
                if isinstance(subject, AccessSubjectNotUser):
                    return AccessMutationRejected(reason=AccessMutationRejectReason.CONTACT_NOT_USER)

            current = await uow.memberships.list_for_group(group_id)
            current_by_id = {membership.contact_id: membership for membership in current}
            requested_ids = set(requested)
            added = tuple(
                GroupMembership(contact_id, group_id)
                for contact_id in requested
                if contact_id not in current_by_id
            )
            removed = tuple(
                membership
                for membership in current
                if membership.contact_id not in requested_ids
            )
            if added or removed:
                await uow.memberships.apply_delta(added=added, removed=removed)
            count = await uow.memberships.recount_group(group_id)
            await uow.commit()
            return GroupMembersReplaced(
                group_id=group_id.value,
                added_contact_ids=tuple(item.contact_id for item in added),
                removed_contact_ids=tuple(item.contact_id for item in removed),
                member_count=count.count,
            )
