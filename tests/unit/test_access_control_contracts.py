from dataclasses import FrozenInstanceError

import pytest
from pydantic import TypeAdapter

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
from gomazon_webasyst.contracts.access_control import (
    AppAccess,
    FiniteRight,
    FullAppAccess,
    GlobalAdminAccess,
    GroupCreate,
    GroupMissing,
    GroupRead,
    GroupResolution,
    LimitedAppAccess,
    NoAppAccess,
    UnlimitedRight,
)
from gomazon_webasyst.contracts.enums import (
    AppAccessKind,
    GroupResolutionKind,
    GroupType,
    UnlimitedRightReason,
)


def test_access_values_are_frozen_hashable_and_validate_domain_shape() -> None:
    group_id = GroupId(7)
    key = PermissionKey(AppId("shop"), RightName("orders.edit"))
    user = UserTarget(42)
    group = GroupTarget(group_id)
    guests = GuestsTarget()
    membership = GroupMembership(contact_id=42, group_id=group_id)

    assert {group_id, key, user, group, guests, membership}
    assert RightValue(-1).value == -1

    with pytest.raises(FrozenInstanceError):
        user.contact_id = 10  # type: ignore[misc]
    with pytest.raises(ValueError):
        GroupId(0)
    with pytest.raises(ValueError):
        UserTarget(0)
    with pytest.raises(ValueError):
        AppId("")
    with pytest.raises(ValueError):
        RightName("")


def test_group_contract_uses_closed_group_type_and_explicit_missing_variant() -> None:
    created = GroupCreate(name="Operators", type=GroupType.GROUP)
    read = GroupRead(
        id=7,
        name="Operators",
        type=GroupType.GROUP,
        member_count=2,
        icon="user",
        sort=0,
        description="",
    )
    missing = GroupMissing(group_id=7)

    assert created.type is GroupType.GROUP
    assert read.type is GroupType.GROUP
    assert missing.kind is GroupResolutionKind.MISSING

    adapter = TypeAdapter(GroupResolution)
    parsed = adapter.validate_python({"kind": "missing", "group_id": 9})
    assert isinstance(parsed, GroupMissing)
    assert parsed.group_id == 9


def test_app_access_is_explicit_variant_family_not_integer_or_bool() -> None:
    variants: tuple[AppAccess, ...] = (
        NoAppAccess(app_id="shop"),
        LimitedAppAccess(app_id="shop"),
        FullAppAccess(app_id="shop"),
        GlobalAdminAccess(app_id="shop"),
    )

    assert [item.kind for item in variants] == [
        AppAccessKind.NONE,
        AppAccessKind.LIMITED,
        AppAccessKind.FULL,
        AppAccessKind.GLOBAL_ADMIN,
    ]

    adapter = TypeAdapter(AppAccess)
    parsed = adapter.validate_python({"kind": "limited", "app_id": "shop"})
    assert isinstance(parsed, LimitedAppAccess)


def test_effective_right_is_finite_or_unlimited_without_nullable_fields() -> None:
    finite = FiniteRight(value=-1)
    global_unlimited = UnlimitedRight(reason=UnlimitedRightReason.GLOBAL_ADMIN)
    app_unlimited = UnlimitedRight(reason=UnlimitedRightReason.APP_FULL_ACCESS)

    assert finite.value == -1
    assert global_unlimited.reason is UnlimitedRightReason.GLOBAL_ADMIN
    assert app_unlimited.reason is UnlimitedRightReason.APP_FULL_ACCESS
    assert all(field.annotation is not type(None) for field in FiniteRight.model_fields.values())
