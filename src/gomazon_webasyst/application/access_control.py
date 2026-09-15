from dataclasses import dataclass

from gomazon_webasyst.application.access_values import (
    AppId,
    GroupId,
    GroupTarget,
    GuestsTarget,
    PermissionKey,
    UserTarget,
)
from gomazon_webasyst.application.ports.access_control_uow import (
    AccessControlUnitOfWork,
    AccessControlUnitOfWorkFactory,
)
from gomazon_webasyst.application.ports.access_subjects import (
    AccessSubjectMissing,
    AccessSubjectNotUser,
)
from gomazon_webasyst.application.ports.rights import RightsSnapshot
from gomazon_webasyst.application.rights_evaluator import RightsEvaluator
from gomazon_webasyst.contracts.access_control import (
    AccessReadRejected,
    AppAccessResolved,
    AppAccessResult,
    EffectiveRightResolved,
    EffectiveRightResult,
    FiniteRightsSnapshot,
    GroupMembersResolved,
    GroupMembersResult,
    GroupMissing,
    GroupRead,
    GroupResolved,
    GroupResolution,
    RightsSnapshotQueryResult,
    RightsSnapshotResolved,
    UserGroupsResolved,
    UserGroupsResult,
)
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.enums import AccessReadRejectReason


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
    return AccessSnapshotLoaded(
        snapshot=await uow.rights.load_for_targets(targets)
    )


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
