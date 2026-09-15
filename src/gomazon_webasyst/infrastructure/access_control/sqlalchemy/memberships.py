from datetime import datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from gomazon_webasyst.application.access_values import GroupId, GroupMembership
from gomazon_webasyst.application.ports.memberships import (
    GroupCountUpdated,
    MembershipAdded,
    MembershipAddResult,
    MembershipAlreadyAbsent,
    MembershipAlreadyPresent,
    MembershipDeltaApplied,
    MembershipRemoved,
    MembershipRemoveResult,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaContactRow,
    WaGroupRow,
    WaUserGroupRow,
)


class SQLAlchemyMembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, contact_id: int) -> tuple[GroupMembership, ...]:
        result = await self._session.execute(
            select(WaUserGroupRow)
            .where(WaUserGroupRow.contact_id == contact_id)
            .order_by(WaUserGroupRow.group_id)
        )
        return tuple(
            GroupMembership(row.contact_id, GroupId(row.group_id))
            for row in result.scalars()
        )

    async def list_for_group(self, group_id: GroupId) -> tuple[GroupMembership, ...]:
        result = await self._session.execute(
            select(WaUserGroupRow)
            .where(WaUserGroupRow.group_id == group_id.value)
            .order_by(WaUserGroupRow.contact_id)
        )
        return tuple(
            GroupMembership(row.contact_id, GroupId(row.group_id))
            for row in result.scalars()
        )

    async def add(self, membership: GroupMembership) -> MembershipAddResult:
        identity = {
            "contact_id": membership.contact_id,
            "group_id": membership.group_id.value,
        }
        row = await self._session.get(WaUserGroupRow, identity)
        if row is not None:
            return MembershipAlreadyPresent(membership)
        self._session.add(
            WaUserGroupRow(
                contact_id=membership.contact_id,
                group_id=membership.group_id.value,
                datetime=datetime.now(),
            )
        )
        await self._session.flush()
        return MembershipAdded(membership)

    async def remove(self, membership: GroupMembership) -> MembershipRemoveResult:
        identity = {
            "contact_id": membership.contact_id,
            "group_id": membership.group_id.value,
        }
        row = await self._session.get(WaUserGroupRow, identity)
        if row is None:
            return MembershipAlreadyAbsent(membership)
        await self._session.delete(row)
        await self._session.flush()
        return MembershipRemoved(membership)

    async def apply_delta(
        self,
        *,
        added: tuple[GroupMembership, ...],
        removed: tuple[GroupMembership, ...],
    ) -> MembershipDeltaApplied:
        for membership in removed:
            await self._session.execute(
                delete(WaUserGroupRow).where(
                    WaUserGroupRow.contact_id == membership.contact_id,
                    WaUserGroupRow.group_id == membership.group_id.value,
                )
            )
        now = datetime.now()
        for membership in added:
            identity = {
                "contact_id": membership.contact_id,
                "group_id": membership.group_id.value,
            }
            existing = await self._session.get(WaUserGroupRow, identity)
            if existing is None:
                self._session.add(
                    WaUserGroupRow(
                        contact_id=membership.contact_id,
                        group_id=membership.group_id.value,
                        datetime=now,
                    )
                )
        await self._session.flush()
        return MembershipDeltaApplied(added=added, removed=removed)

    async def recount_group(self, group_id: GroupId) -> GroupCountUpdated:
        count_result = await self._session.execute(
            select(func.count())
            .select_from(WaUserGroupRow)
            .join(WaContactRow, WaContactRow.id == WaUserGroupRow.contact_id)
            .where(
                WaUserGroupRow.group_id == group_id.value,
                WaContactRow.is_user > 0,
            )
        )
        count = int(count_result.scalar_one())
        await self._session.execute(
            update(WaGroupRow)
            .where(WaGroupRow.id == group_id.value)
            .values(cnt=count)
        )
        await self._session.flush()
        return GroupCountUpdated(group_id=group_id, count=count)
