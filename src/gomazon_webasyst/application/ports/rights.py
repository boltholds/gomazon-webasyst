from dataclasses import dataclass
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.access_values import (
    AccessTarget,
    AppId,
    PermissionKey,
    RightValue,
)
from gomazon_webasyst.application.rights_mutation_policy import RightsMutationPlan


@dataclass(slots=True, frozen=True)
class GlobalAccessAssignment:
    target: AccessTarget
    value: RightValue


@dataclass(slots=True, frozen=True)
class AppAccessAssignment:
    target: AccessTarget
    app_id: AppId
    value: RightValue


@dataclass(slots=True, frozen=True)
class NamedRightAssignment:
    target: AccessTarget
    key: PermissionKey
    value: RightValue


RightAssignment: TypeAlias = (
    GlobalAccessAssignment | AppAccessAssignment | NamedRightAssignment
)


@dataclass(slots=True, frozen=True)
class RightsSnapshot:
    assignments: tuple[RightAssignment, ...]


@dataclass(slots=True, frozen=True)
class RightsPlanApplied:
    operation_count: int


@dataclass(slots=True, frozen=True)
class RightsDeleted:
    target: AccessTarget
    deleted_count: int


class RightsRepository(Protocol):
    async def load_for_targets(
        self,
        targets: tuple[AccessTarget, ...],
    ) -> RightsSnapshot: ...

    async def execute_plan(self, plan: RightsMutationPlan) -> RightsPlanApplied: ...

    async def delete_all_for_target(self, target: AccessTarget) -> RightsDeleted: ...
