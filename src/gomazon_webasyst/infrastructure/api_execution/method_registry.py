from gomazon_webasyst.application.api_execution.entities.method_definition import ApiMethodDefinition
from gomazon_webasyst.application.api_execution.vo.method import ApiMethodTarget
from gomazon_webasyst.application.ports.api_method_registry import (
    ApiMethodMissing,
    ApiMethodRegistered,
    ApiMethodRegistrationRejected,
    ApiMethodRegistrationResult,
    ApiMethodResolution,
    ApiMethodResolved,
)


class InMemoryApiMethodRegistry:
    def __init__(self) -> None:
        self._definitions: dict[ApiMethodTarget, ApiMethodDefinition] = {}

    def register(self, definition: ApiMethodDefinition) -> ApiMethodRegistrationResult:
        if definition.target in self._definitions:
            return ApiMethodRegistrationRejected(target=definition.target)
        self._definitions[definition.target] = definition
        return ApiMethodRegistered(definition=definition)

    def resolve(self, target: ApiMethodTarget) -> ApiMethodResolution:
        if target not in self._definitions:
            return ApiMethodMissing(target=target)
        return ApiMethodResolved(definition=self._definitions[target])
