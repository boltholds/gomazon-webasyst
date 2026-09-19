from dataclasses import dataclass
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.api_execution.entities.method_definition import ApiMethodDefinition
from gomazon_webasyst.application.api_execution.vo.method import ApiMethodTarget


@dataclass(slots=True, frozen=True)
class ApiMethodRegistered:
    definition: ApiMethodDefinition


@dataclass(slots=True, frozen=True)
class ApiMethodRegistrationRejected:
    target: ApiMethodTarget


ApiMethodRegistrationResult: TypeAlias = ApiMethodRegistered | ApiMethodRegistrationRejected


@dataclass(slots=True, frozen=True)
class ApiMethodResolved:
    definition: ApiMethodDefinition


@dataclass(slots=True, frozen=True)
class ApiMethodMissing:
    target: ApiMethodTarget


ApiMethodResolution: TypeAlias = ApiMethodResolved | ApiMethodMissing


class ApiMethodRegistry(Protocol):
    def register(self, definition: ApiMethodDefinition) -> ApiMethodRegistrationResult: ...
    def resolve(self, target: ApiMethodTarget) -> ApiMethodResolution: ...
