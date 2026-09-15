from gomazon_webasyst.application.access_values import (
    AccessTarget,
    AppId,
    PermissionKey,
    RightValue,
)
from gomazon_webasyst.application.ports.access_semantics import AccessSemantics, GlobalControlApp
from gomazon_webasyst.application.rights_mutation_policy import (
    DeleteAllTargetRights,
    DeleteAppRights,
    DeleteExactRight,
    RightsMutationPlan,
    RightsMutationPlanned,
    RightsMutationPlanningResult,
    RightsMutationRejected,
    UpsertAppAccess,
    UpsertGlobalAccess,
    UpsertNamedRight,
)
from gomazon_webasyst.contracts.enums import (
    AppAccessMode,
    GlobalAdminMode,
    RightsMutationRejectReason,
)


_RESERVED_BACKEND_RIGHT = "backend"


class LegacyRightsMutationPolicy:
    def __init__(self, *, app_semantics: AccessSemantics) -> None:
        self._app_semantics = app_semantics

    def plan_named_assign(
        self,
        target: AccessTarget,
        key: PermissionKey,
        value: RightValue,
    ) -> RightsMutationPlanningResult:
        if key.name.value == _RESERVED_BACKEND_RIGHT:
            return RightsMutationRejected(RightsMutationRejectReason.RESERVED_RIGHT)
        if value.value == 0:
            return RightsMutationRejected(RightsMutationRejectReason.ZERO_VALUE)
        return RightsMutationPlanned(
            RightsMutationPlan((UpsertNamedRight(target, key, value),))
        )

    def plan_named_revoke(
        self,
        target: AccessTarget,
        key: PermissionKey,
    ) -> RightsMutationPlanningResult:
        if key.name.value == _RESERVED_BACKEND_RIGHT:
            return RightsMutationRejected(RightsMutationRejectReason.RESERVED_RIGHT)
        return RightsMutationPlanned(
            RightsMutationPlan((DeleteExactRight(target, key),))
        )

    def plan_app_access(
        self,
        target: AccessTarget,
        app_id: AppId,
        mode: AppAccessMode,
    ) -> RightsMutationPlanningResult:
        if isinstance(self._app_semantics.classify_app(app_id), GlobalControlApp):
            return RightsMutationRejected(RightsMutationRejectReason.GLOBAL_CONTROL_APP)
        if mode is AppAccessMode.LIMITED:
            operations = (UpsertAppAccess(target, app_id, RightValue(1)),)
        elif mode is AppAccessMode.NONE:
            operations = (DeleteAppRights(target, app_id),)
        else:
            operations = (
                DeleteAppRights(target, app_id),
                UpsertAppAccess(target, app_id, RightValue(2)),
            )
        return RightsMutationPlanned(RightsMutationPlan(operations))

    def plan_global_access(
        self,
        target: AccessTarget,
        mode: GlobalAdminMode,
    ) -> RightsMutationPlanningResult:
        if mode is GlobalAdminMode.DISABLED:
            operations = (DeleteAllTargetRights(target),)
        else:
            operations = (
                DeleteAllTargetRights(target),
                UpsertGlobalAccess(target, RightValue(1)),
            )
        return RightsMutationPlanned(RightsMutationPlan(operations))
