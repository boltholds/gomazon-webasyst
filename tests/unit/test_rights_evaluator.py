from gomazon_webasyst.application.access_values import (
    AppId,
    GroupId,
    GroupTarget,
    GuestsTarget,
    PermissionKey,
    RightName,
    RightValue,
    UserTarget,
)
from gomazon_webasyst.application.ports.rights import (
    AppAccessAssignment,
    GlobalAccessAssignment,
    NamedRightAssignment,
    RightsSnapshot,
)
from gomazon_webasyst.application.rights_evaluator import RightsEvaluator
from gomazon_webasyst.compatibility.webasyst.access_control.evaluation import (
    ExactThenLegacyAllFallback,
    WebasystAccessSemantics,
)
from gomazon_webasyst.contracts.access_control import (
    FiniteRight,
    FullAppAccess,
    GlobalAdminAccess,
    LimitedAppAccess,
    NoAppAccess,
    UnlimitedRight,
)
from gomazon_webasyst.contracts.enums import UnlimitedRightReason


def evaluator() -> RightsEvaluator:
    return RightsEvaluator(
        app_semantics=WebasystAccessSemantics(),
        fallback_policy=ExactThenLegacyAllFallback(),
    )


def test_effective_named_right_uses_max_across_personal_groups_and_guests() -> None:
    key = PermissionKey(AppId("shop"), RightName("orders.edit"))
    snapshot = RightsSnapshot(
        assignments=(
            AppAccessAssignment(UserTarget(42), AppId("shop"), RightValue(1)),
            NamedRightAssignment(UserTarget(42), key, RightValue(1)),
            NamedRightAssignment(GroupTarget(GroupId(7)), key, RightValue(3)),
            NamedRightAssignment(GuestsTarget(), key, RightValue(2)),
        )
    )

    result = evaluator().effective_right(snapshot, key)

    assert isinstance(result, FiniteRight)
    assert result.value == 3


def test_named_right_is_zero_without_application_backend_access() -> None:
    key = PermissionKey(AppId("shop"), RightName("orders.edit"))
    snapshot = RightsSnapshot(
        assignments=(NamedRightAssignment(UserTarget(42), key, RightValue(5)),)
    )

    result = evaluator().effective_right(snapshot, key)

    assert isinstance(result, FiniteRight)
    assert result.value == 0
    assert isinstance(evaluator().app_access(snapshot, AppId("shop")), NoAppAccess)


def test_limited_and_full_application_access_are_distinct() -> None:
    limited = RightsSnapshot(
        assignments=(AppAccessAssignment(UserTarget(42), AppId("shop"), RightValue(1)),)
    )
    full = RightsSnapshot(
        assignments=(AppAccessAssignment(UserTarget(42), AppId("shop"), RightValue(2)),)
    )

    assert isinstance(evaluator().app_access(limited, AppId("shop")), LimitedAppAccess)
    assert isinstance(evaluator().app_access(full, AppId("shop")), FullAppAccess)

    right = evaluator().effective_right(
        full,
        PermissionKey(AppId("shop"), RightName("orders.edit")),
    )
    assert isinstance(right, UnlimitedRight)
    assert right.reason is UnlimitedRightReason.APP_FULL_ACCESS


def test_global_admin_overrides_regular_application_rights() -> None:
    snapshot = RightsSnapshot(
        assignments=(GlobalAccessAssignment(UserTarget(42), RightValue(1)),)
    )

    access = evaluator().app_access(snapshot, AppId("shop"))
    right = evaluator().effective_right(
        snapshot,
        PermissionKey(AppId("shop"), RightName("orders.edit")),
    )

    assert isinstance(access, GlobalAdminAccess)
    assert isinstance(right, UnlimitedRight)
    assert right.reason is UnlimitedRightReason.GLOBAL_ADMIN


def test_global_control_backend_one_does_not_make_its_named_rights_unlimited() -> None:
    key = PermissionKey(AppId("webasyst"), RightName("dashboard.edit"))
    snapshot = RightsSnapshot(
        assignments=(
            GlobalAccessAssignment(UserTarget(42), RightValue(1)),
            NamedRightAssignment(UserTarget(42), key, RightValue(1)),
        )
    )

    access = evaluator().app_access(snapshot, AppId("webasyst"))
    right = evaluator().effective_right(snapshot, key)

    assert isinstance(access, GlobalAdminAccess)
    assert isinstance(right, FiniteRight)
    assert right.value == 1


def test_legacy_all_fallback_is_used_only_after_exact_zero() -> None:
    app = AppId("team")
    exact = PermissionKey(app, RightName("manage_group.7"))
    fallback = PermissionKey(app, RightName("manage_group.all"))
    snapshot = RightsSnapshot(
        assignments=(
            AppAccessAssignment(UserTarget(42), app, RightValue(1)),
            NamedRightAssignment(UserTarget(42), fallback, RightValue(5)),
        )
    )

    result = evaluator().effective_right(snapshot, exact)

    assert isinstance(result, FiniteRight)
    assert result.value == 5


def test_negative_exact_value_suppresses_legacy_all_fallback() -> None:
    app = AppId("team")
    exact = PermissionKey(app, RightName("manage_group.7"))
    fallback = PermissionKey(app, RightName("manage_group.all"))
    snapshot = RightsSnapshot(
        assignments=(
            AppAccessAssignment(UserTarget(42), app, RightValue(1)),
            NamedRightAssignment(UserTarget(42), exact, RightValue(-1)),
            NamedRightAssignment(UserTarget(42), fallback, RightValue(5)),
        )
    )

    result = evaluator().effective_right(snapshot, exact)

    assert isinstance(result, FiniteRight)
    assert result.value == -1
