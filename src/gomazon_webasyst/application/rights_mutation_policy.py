from dataclasses import dataclass
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.access_values import (
    AccessTarget,
    AppId,
    PermissionKey,
    RightValue,
)
from gomazon_webasyst.contracts.enums import (
    AppAccessMode,
    GlobalAdminMode,
    RightsMutationRejectReason,
)


@dataclass(slots=True, frozen=True)
class DeleteAllTargetRights:
    target: AccessTarget


@dataclass(slots=True, frozen=True)
class DeleteAppRights:
    target: AccessTarget
    app_id: AppId


@dataclass(slots=True, frozen=True)
class DeleteExactRight:
    target: AccessTarget
    key: PermissionKey


@dataclass(slots=True, frozen=True)
class UpsertGlobalAccess:
    target: AccessTarget
    value: RightValue


@dataclass(slots=True, frozen=True)
class UpsertAppAccess:
    target: AccessTarget
    app_id: AppId
    value: RightValue


@dataclass(slots=True, frozen=True)
class UpsertNamedRight:
    target: AccessTarget
    key: PermissionKey
    value: RightValue


RightsMutationOperation: TypeAlias = (
    DeleteAllTargetRights
    | DeleteAppRights
    | DeleteExactRight
    | UpsertGlobalAccess
    | UpsertAppAccess
    | UpsertNamedRight
)


@dataclass(slots=True, frozen=True)
class RightsMutationPlan:
    operations: tuple[RightsMutationOperation, ...]


@dataclass(slots=True, frozen=True)
class RightsMutationPlanned:
    plan: RightsMutationPlan


@dataclass(slots=True, frozen=True)
class RightsMutationRejected:
    reason: RightsMutationRejectReason


RightsMutationPlanningResult: TypeAlias = RightsMutationPlanned | RightsMutationRejected


class RightsMutationPolicy(Protocol):
    def plan_named_assign(
        self,
        target: AccessTarget,
        key: PermissionKey,
        value: RightValue,
    ) -> RightsMutationPlanningResult: ...

    def plan_named_revoke(
        self,
        target: AccessTarget,
        key: PermissionKey,
    ) -> RightsMutationPlanningResult: ...

    def plan_app_access(
        self,
        target: AccessTarget,
        app_id: AppId,
        mode: AppAccessMode,
    ) -> RightsMutationPlanningResult: ...

    def plan_global_access(
        self,
        target: AccessTarget,
        mode: GlobalAdminMode,
    ) -> RightsMutationPlanningResult: ...
