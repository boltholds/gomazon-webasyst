from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.application.access_values import (
    AccessTarget,
    AppId,
    PermissionKey,
    RightValue,
)


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
