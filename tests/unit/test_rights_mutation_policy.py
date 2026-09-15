from gomazon_webasyst.application.access_values import (
    AppId,
    PermissionKey,
    RightName,
    RightValue,
    UserTarget,
)
from gomazon_webasyst.application.rights_mutation_policy import (
    DeleteAllTargetRights,
    DeleteAppRights,
    DeleteExactRight,
    RightsMutationPlanned,
    RightsMutationRejected,
    UpsertAppAccess,
    UpsertGlobalAccess,
    UpsertNamedRight,
)
from gomazon_webasyst.compatibility.webasyst.access_control.evaluation import WebasystAccessSemantics
from gomazon_webasyst.compatibility.webasyst.access_control.mutation import LegacyRightsMutationPolicy
from gomazon_webasyst.contracts.enums import (
    AppAccessMode,
    GlobalAdminMode,
    RightsMutationRejectReason,
)


def policy() -> LegacyRightsMutationPolicy:
    return LegacyRightsMutationPolicy(app_semantics=WebasystAccessSemantics())


def test_global_enable_deletes_every_target_right_then_sets_global_access() -> None:
    target = UserTarget(42)

    result = policy().plan_global_access(target, GlobalAdminMode.ENABLED)

    assert isinstance(result, RightsMutationPlanned)
    assert result.plan.operations == (
        DeleteAllTargetRights(target),
        UpsertGlobalAccess(target, RightValue(1)),
    )


def test_global_disable_deletes_every_target_right_and_leaves_no_assignment() -> None:
    target = UserTarget(42)

    result = policy().plan_global_access(target, GlobalAdminMode.DISABLED)

    assert isinstance(result, RightsMutationPlanned)
    assert result.plan.operations == (DeleteAllTargetRights(target),)


def test_app_limited_preserves_granular_scope() -> None:
    target = UserTarget(42)
    app = AppId("shop")

    result = policy().plan_app_access(target, app, AppAccessMode.LIMITED)

    assert isinstance(result, RightsMutationPlanned)
    assert result.plan.operations == (
        UpsertAppAccess(target, app, RightValue(1)),
    )


def test_app_none_deletes_scope_without_backend_upsert() -> None:
    target = UserTarget(42)
    app = AppId("shop")

    result = policy().plan_app_access(target, app, AppAccessMode.NONE)

    assert isinstance(result, RightsMutationPlanned)
    assert result.plan.operations == (DeleteAppRights(target, app),)


def test_app_full_deletes_scope_then_sets_backend_two() -> None:
    target = UserTarget(42)
    app = AppId("shop")

    result = policy().plan_app_access(target, app, AppAccessMode.FULL)

    assert isinstance(result, RightsMutationPlanned)
    assert result.plan.operations == (
        DeleteAppRights(target, app),
        UpsertAppAccess(target, app, RightValue(2)),
    )


def test_named_right_assign_and_revoke_are_exact_operations() -> None:
    target = UserTarget(42)
    key = PermissionKey(AppId("shop"), RightName("orders.edit"))

    assigned = policy().plan_named_assign(target, key, RightValue(3))
    revoked = policy().plan_named_revoke(target, key)

    assert isinstance(assigned, RightsMutationPlanned)
    assert assigned.plan.operations == (UpsertNamedRight(target, key, RightValue(3)),)
    assert isinstance(revoked, RightsMutationPlanned)
    assert revoked.plan.operations == (DeleteExactRight(target, key),)


def test_named_zero_assignment_is_typed_rejection() -> None:
    result = policy().plan_named_assign(
        UserTarget(42),
        PermissionKey(AppId("shop"), RightName("orders.edit")),
        RightValue(0),
    )

    assert isinstance(result, RightsMutationRejected)
    assert result.reason is RightsMutationRejectReason.ZERO_VALUE


def test_reserved_backend_named_mutation_is_typed_rejection() -> None:
    result = policy().plan_named_assign(
        UserTarget(42),
        PermissionKey(AppId("shop"), RightName("backend")),
        RightValue(1),
    )

    assert isinstance(result, RightsMutationRejected)
    assert result.reason is RightsMutationRejectReason.RESERVED_RIGHT


def test_global_control_app_cannot_use_normal_app_access_mutation() -> None:
    result = policy().plan_app_access(
        UserTarget(42),
        AppId("webasyst"),
        AppAccessMode.LIMITED,
    )

    assert isinstance(result, RightsMutationRejected)
    assert result.reason is RightsMutationRejectReason.GLOBAL_CONTROL_APP
