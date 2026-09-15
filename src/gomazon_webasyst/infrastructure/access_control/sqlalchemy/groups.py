from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gomazon_webasyst.application.access_values import GroupId
from gomazon_webasyst.application.ports.groups import (
    GroupDeleteMissing,
    GroupDeleteResult,
    GroupDeleted,
)
from gomazon_webasyst.contracts.access_control import (
    GroupCreate,
    GroupMissing,
    GroupRead,
    GroupResolution,
    GroupResolved,
    GroupUpdate,
)
from gomazon_webasyst.contracts.enums import GroupType
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import WaGroupRow


def _read(row: WaGroupRow) -> GroupRead:
    return GroupRead(
        id=row.id,
        name=row.name,
        type=GroupType(row.type),
        member_count=row.cnt,
        icon=row.icon or "user",
        sort=row.sort if row.sort is not None else 0,
        description=row.description or "",
    )


class SQLAlchemyGroupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: GroupCreate) -> GroupRead:
        row = WaGroupRow(
            name=data.name,
            cnt=0,
            icon=data.icon,
            sort=data.sort,
            type=data.type.value,
            description=data.description,
        )
        self._session.add(row)
        await self._session.flush()
        return _read(row)

    async def get(self, group_id: GroupId) -> GroupResolution:
        row = await self._session.get(WaGroupRow, group_id.value)
        if row is None:
            return GroupMissing(group_id=group_id.value)
        return GroupResolved(group=_read(row))

    async def list(self) -> tuple[GroupRead, ...]:
        result = await self._session.execute(
            select(WaGroupRow).order_by(WaGroupRow.type, WaGroupRow.sort, WaGroupRow.name)
        )
        return tuple(_read(row) for row in result.scalars())

    async def update(self, group_id: GroupId, data: GroupUpdate) -> GroupResolution:
        row = await self._session.get(WaGroupRow, group_id.value)
        if row is None:
            return GroupMissing(group_id=group_id.value)
        patch = data.model_dump(exclude_unset=True)
        for field, value in patch.items():
            if field == "type":
                value = value.value if isinstance(value, GroupType) else value
            setattr(row, field, value)
        await self._session.flush()
        return GroupResolved(group=_read(row))

    async def delete(self, group_id: GroupId) -> GroupDeleteResult:
        row = await self._session.get(WaGroupRow, group_id.value)
        if row is None:
            return GroupDeleteMissing(group_id)
        await self._session.delete(row)
        await self._session.flush()
        return GroupDeleted(group_id)
