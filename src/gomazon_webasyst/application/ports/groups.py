from dataclasses import dataclass
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.access_values import GroupId
from gomazon_webasyst.contracts.access_control import (
    GroupCreate,
    GroupRead,
    GroupResolution,
    GroupUpdate,
)


@dataclass(slots=True, frozen=True)
class GroupDeleted:
    group_id: GroupId


@dataclass(slots=True, frozen=True)
class GroupDeleteMissing:
    group_id: GroupId


GroupDeleteResult: TypeAlias = GroupDeleted | GroupDeleteMissing


class GroupRepository(Protocol):
    async def create(self, data: GroupCreate) -> GroupRead: ...

    async def get(self, group_id: GroupId) -> GroupResolution: ...

    async def list(self) -> tuple[GroupRead, ...]: ...

    async def update(self, group_id: GroupId, data: GroupUpdate) -> GroupResolution: ...

    async def delete(self, group_id: GroupId) -> GroupDeleteResult: ...
