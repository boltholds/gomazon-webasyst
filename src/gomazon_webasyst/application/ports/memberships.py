from dataclasses import dataclass
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.access_values import GroupId, GroupMembership


@dataclass(slots=True, frozen=True)
class MembershipAdded:
    membership: GroupMembership


@dataclass(slots=True, frozen=True)
class MembershipAlreadyPresent:
    membership: GroupMembership


MembershipAddResult: TypeAlias = MembershipAdded | MembershipAlreadyPresent


@dataclass(slots=True, frozen=True)
class MembershipRemoved:
    membership: GroupMembership


@dataclass(slots=True, frozen=True)
class MembershipAlreadyAbsent:
    membership: GroupMembership


MembershipRemoveResult: TypeAlias = MembershipRemoved | MembershipAlreadyAbsent


@dataclass(slots=True, frozen=True)
class MembershipDeltaApplied:
    added: tuple[GroupMembership, ...]
    removed: tuple[GroupMembership, ...]


@dataclass(slots=True, frozen=True)
class GroupCountUpdated:
    group_id: GroupId
    count: int


class MembershipRepository(Protocol):
    async def list_for_user(self, contact_id: int) -> tuple[GroupMembership, ...]: ...

    async def list_for_group(self, group_id: GroupId) -> tuple[GroupMembership, ...]: ...

    async def add(self, membership: GroupMembership) -> MembershipAddResult: ...

    async def remove(self, membership: GroupMembership) -> MembershipRemoveResult: ...

    async def apply_delta(
        self,
        *,
        added: tuple[GroupMembership, ...],
        removed: tuple[GroupMembership, ...],
    ) -> MembershipDeltaApplied: ...

    async def recount_group(self, group_id: GroupId) -> GroupCountUpdated: ...
