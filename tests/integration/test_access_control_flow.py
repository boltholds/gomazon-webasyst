from datetime import datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.application.application_registry import (
    ApplicationCatalog,
    InstallationManifest,
    InstalledApplication,
    StaticApplicationRegistry,
)
from gomazon_webasyst.application.access_values import (
    AppId,
    GroupId,
    GroupMembership,
    GroupTarget,
    PermissionKey,
    RightName,
    RightValue,
    UserTarget,
)
from gomazon_webasyst.composition.access_control import create_access_control_use_cases
from gomazon_webasyst.contracts.applications import ApplicationDescriptor
from gomazon_webasyst.contracts.access_control import (
    AccessMutationRejected,
    AppAccessSet,
    EffectiveRightResolved,
    FiniteRight,
    GlobalAdminAccess,
    GlobalAdminAccessSet,
    GroupCreate,
    GroupCreated,
    GroupDeleted,
    GroupMembershipAdded,
    GroupMembershipRemoved,
    GroupMembersReplaced,
    NoAppAccess,
    RightAssigned,
    RightRevoked,
    UnlimitedRight,
)
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.enums import (
    AccessMutationRejectReason,
    AppAccessMode,
    GlobalAdminMode,
    UnlimitedRightReason,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaContactRightRow,
    WaContactRow,
    WaGroupRow,
    WaUserGroupRow,
)


@pytest.mark.asyncio
async def test_access_control_vertical_flow_with_real_legacy_tables() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async with sessions() as session:
        session.add_all(
            [
                WaContactRow(
                    id=1,
                    name="Root",
                    login="root",
                    password="x",
                    is_user=1,
                    create_datetime=datetime(2026, 1, 1),
                ),
                WaContactRow(
                    id=42,
                    name="User",
                    login="user42",
                    password="x",
                    is_user=1,
                    create_datetime=datetime(2026, 1, 1),
                ),
                WaContactRow(
                    id=43,
                    name="User 43",
                    login="user43",
                    password="x",
                    is_user=1,
                    create_datetime=datetime(2026, 1, 1),
                ),
                WaGroupRow(id=7, name="Legacy group", cnt=1, type="group"),
                WaUserGroupRow(
                    contact_id=42,
                    group_id=7,
                    datetime=datetime(2026, 1, 1),
                ),
                WaContactRightRow(
                    group_id=-1,
                    app_id="webasyst",
                    name="backend",
                    value=1,
                ),
                WaContactRightRow(
                    group_id=-42,
                    app_id="shop",
                    name="backend",
                    value=1,
                ),
                WaContactRightRow(
                    group_id=-42,
                    app_id="shop",
                    name="orders.edit",
                    value=1,
                ),
                WaContactRightRow(
                    group_id=7,
                    app_id="shop",
                    name="orders.edit",
                    value=4,
                ),
                WaContactRightRow(
                    group_id=0,
                    app_id="shop",
                    name="orders.edit",
                    value=2,
                ),
            ]
        )
        await session.commit()

    application_registry = StaticApplicationRegistry(
        ApplicationCatalog(
            applications=(
                ApplicationDescriptor(id=AppId("shop"), name="Shop"),
            ),
        ),
        InstallationManifest(
            apps=(InstalledApplication(AppId("shop")),),
        ),
    )
    access = create_access_control_use_cases(
        sessions,
        application_registry,
    )
    root = AuthenticatedSubject(id=1, login="root")
    user = AuthenticatedSubject(id=42, login="user42")
    user43 = AuthenticatedSubject(id=43, login="user43")
    orders_edit = PermissionKey(AppId("shop"), RightName("orders.edit"))

    effective = await access.get_effective_right(user, orders_edit)
    assert isinstance(effective, EffectiveRightResolved)
    assert isinstance(effective.right, FiniteRight)
    assert effective.right.value == 4

    unknown_app_read = await access.get_effective_right(
        user,
        PermissionKey(AppId("legacy_unknown"), RightName("orders.edit")),
    )
    assert isinstance(unknown_app_read, EffectiveRightResolved)
    assert isinstance(unknown_app_read.right, FiniteRight)
    assert unknown_app_read.right.value == 0

    created = await access.create_group(root, GroupCreate(name="Editors"))
    assert isinstance(created, GroupCreated)
    created_group_id = GroupId(created.group.id)

    added = await access.add_group_member(
        root,
        GroupMembership(42, created_group_id),
    )
    assert isinstance(added, GroupMembershipAdded)
    assert added.member_count == 1

    removed = await access.remove_group_member(
        root,
        GroupMembership(42, created_group_id),
    )
    assert isinstance(removed, GroupMembershipRemoved)
    assert removed.member_count == 0

    added_again = await access.add_group_member(
        root,
        GroupMembership(42, created_group_id),
    )
    assert isinstance(added_again, GroupMembershipAdded)

    replaced = await access.replace_group_members(root, created_group_id, (43,))
    assert isinstance(replaced, GroupMembersReplaced)
    assert replaced.added_contact_ids == (43,)
    assert replaced.removed_contact_ids == (42,)
    assert replaced.member_count == 1

    full = await access.set_app_access(
        root,
        UserTarget(42),
        AppId("shop"),
        AppAccessMode.FULL,
    )
    assert isinstance(full, AppAccessSet)
    full_right = await access.get_effective_right(
        user,
        PermissionKey(AppId("shop"), RightName("anything")),
    )
    assert isinstance(full_right, EffectiveRightResolved)
    assert isinstance(full_right.right, UnlimitedRight)
    assert full_right.right.reason is UnlimitedRightReason.APP_FULL_ACCESS

    limited = await access.set_app_access(
        root,
        UserTarget(42),
        AppId("shop"),
        AppAccessMode.LIMITED,
    )
    assert isinstance(limited, AppAccessSet)

    export_key = PermissionKey(AppId("shop"), RightName("export"))
    assigned = await access.assign_right(root, UserTarget(42), export_key, RightValue(3))
    assert isinstance(assigned, RightAssigned)
    assigned_read = await access.get_effective_right(user, export_key)
    assert isinstance(assigned_read, EffectiveRightResolved)
    assert isinstance(assigned_read.right, FiniteRight)
    assert assigned_read.right.value == 3

    revoked = await access.revoke_right(root, UserTarget(42), export_key)
    assert isinstance(revoked, RightRevoked)
    revoked_read = await access.get_effective_right(user, export_key)
    assert isinstance(revoked_read, EffectiveRightResolved)
    assert isinstance(revoked_read.right, FiniteRight)
    assert revoked_read.right.value == 0

    none = await access.set_app_access(
        root,
        UserTarget(42),
        AppId("shop"),
        AppAccessMode.NONE,
    )
    assert isinstance(none, AppAccessSet)
    no_access = await access.get_app_access(user, AppId("shop"))
    assert isinstance(no_access.access, NoAppAccess)

    global_admin = await access.set_global_admin_access(
        root,
        UserTarget(43),
        GlobalAdminMode.ENABLED,
    )
    assert isinstance(global_admin, GlobalAdminAccessSet)
    user43_access = await access.get_app_access(user43, AppId("shop"))
    assert isinstance(user43_access.access, GlobalAdminAccess)

    group_right_key = PermissionKey(AppId("shop"), RightName("group.special"))
    group_assignment = await access.assign_right(
        root,
        GroupTarget(created_group_id),
        group_right_key,
        RightValue(1),
    )
    assert isinstance(group_assignment, RightAssigned)

    deleted = await access.delete_group(root, created_group_id)
    assert isinstance(deleted, GroupDeleted)

    async with sessions() as session:
        membership_count = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(WaUserGroupRow)
                    .where(WaUserGroupRow.group_id == created_group_id.value)
                )
            ).scalar_one()
        )
        right_count = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(WaContactRightRow)
                    .where(WaContactRightRow.group_id == created_group_id.value)
                )
            ).scalar_one()
        )
        group_count = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(WaGroupRow)
                    .where(WaGroupRow.id == created_group_id.value)
                )
            ).scalar_one()
        )
    assert membership_count == 0
    assert right_count == 0
    assert group_count == 0

    denied = await access.create_group(user, GroupCreate(name="Forbidden"))
    assert isinstance(denied, AccessMutationRejected)
    assert denied.reason is AccessMutationRejectReason.ACCESS_DENIED

    await engine.dispose()
