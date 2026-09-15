from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

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
    AccessSubjectNotUser,
    AccessSubjectResolved,
)
from gomazon_webasyst.application.ports.memberships import (
    MembershipAdded,
    MembershipAlreadyPresent,
    MembershipRemoved,
)
from gomazon_webasyst.application.ports.rights import (
    AppAccessAssignment,
    GlobalAccessAssignment,
    NamedRightAssignment,
)
from gomazon_webasyst.application.rights_mutation_policy import (
    DeleteAppRights,
    RightsMutationPlan,
    UpsertAppAccess,
    UpsertGlobalAccess,
    UpsertNamedRight,
)
from gomazon_webasyst.contracts.access_control import GroupCreate, GroupMissing, GroupResolved, GroupUpdate
from gomazon_webasyst.contracts.enums import GroupType
from gomazon_webasyst.infrastructure.access_control.sqlalchemy.groups import SQLAlchemyGroupRepository
from gomazon_webasyst.infrastructure.access_control.sqlalchemy.memberships import SQLAlchemyMembershipRepository
from gomazon_webasyst.infrastructure.access_control.sqlalchemy.rights import SQLAlchemyRightsRepository
from gomazon_webasyst.infrastructure.access_control.sqlalchemy.subjects import SQLAlchemyAccessSubjectStore
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import WaContactRow
from gomazon_webasyst.compatibility.webasyst.access_control.principals import WebasystPrincipalCodec


@pytest.mark.asyncio
async def test_acl_repositories_round_trip_legacy_tables_and_typed_contracts() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async with sessions() as session:
        session.add_all(
            [
                WaContactRow(
                    id=42,
                    name="Admin",
                    login="admin",
                    password="x",
                    is_user=1,
                    create_datetime=datetime(2026, 1, 1),
                ),
                WaContactRow(
                    id=43,
                    name="Contact",
                    login="contact",
                    password="x",
                    is_user=0,
                    create_datetime=datetime(2026, 1, 1),
                ),
            ]
        )
        await session.commit()

    async with sessions() as session:
        groups = SQLAlchemyGroupRepository(session)
        memberships = SQLAlchemyMembershipRepository(session)
        subjects = SQLAlchemyAccessSubjectStore(session)
        rights = SQLAlchemyRightsRepository(session, principal_codec=WebasystPrincipalCodec())

        created = await groups.create(GroupCreate(name="Operators", type=GroupType.GROUP))
        group_id = GroupId(created.id)
        assert created.icon == "user"
        assert created.sort == 0
        assert created.description == ""

        resolved = await groups.get(group_id)
        assert isinstance(resolved, GroupResolved)
        assert resolved.group.name == "Operators"
        assert isinstance(await groups.get(GroupId(999)), GroupMissing)

        updated = await groups.update(group_id, GroupUpdate(name="Engineers"))
        assert isinstance(updated, GroupResolved)
        assert updated.group.name == "Engineers"

        assert isinstance(await subjects.resolve(42), AccessSubjectResolved)
        assert isinstance(await subjects.resolve(43), AccessSubjectNotUser)

        membership = GroupMembership(42, group_id)
        assert isinstance(await memberships.add(membership), MembershipAdded)
        assert isinstance(await memberships.add(membership), MembershipAlreadyPresent)
        count = await memberships.recount_group(group_id)
        assert count.count == 1
        assert await memberships.list_for_user(42) == (membership,)
        assert await memberships.list_for_group(group_id) == (membership,)

        target = UserTarget(42)
        key = PermissionKey(AppId("shop"), RightName("orders.edit"))
        applied = await rights.execute_plan(
            RightsMutationPlan(
                (
                    UpsertGlobalAccess(target, RightValue(1)),
                    UpsertAppAccess(GroupTarget(group_id), AppId("shop"), RightValue(1)),
                    UpsertNamedRight(GuestsTarget(), key, RightValue(3)),
                )
            )
        )
        assert applied.operation_count == 3

        snapshot = await rights.load_for_targets((target, GroupTarget(group_id), GuestsTarget()))
        assert GlobalAccessAssignment(target, RightValue(1)) in snapshot.assignments
        assert AppAccessAssignment(GroupTarget(group_id), AppId("shop"), RightValue(1)) in snapshot.assignments
        assert NamedRightAssignment(GuestsTarget(), key, RightValue(3)) in snapshot.assignments

        await rights.execute_plan(RightsMutationPlan((DeleteAppRights(GroupTarget(group_id), AppId("shop")),)))
        after_delete = await rights.load_for_targets((GroupTarget(group_id),))
        assert after_delete.assignments == ()

        assert isinstance(await memberships.remove(membership), MembershipRemoved)
        assert (await memberships.recount_group(group_id)).count == 0

        await session.rollback()

    await engine.dispose()
