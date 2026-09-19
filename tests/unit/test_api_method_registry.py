from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_execution.entities.method_definition import ApiMethodDefinition
from gomazon_webasyst.application.api_execution.vo.method import ApiHttpMethod, ApiMethodName, ApiMethodTarget
from gomazon_webasyst.application.ports.api_method_registry import (
    ApiMethodMissing,
    ApiMethodRegistered,
    ApiMethodRegistrationRejected,
    ApiMethodResolved,
)
from gomazon_webasyst.infrastructure.api_execution.method_registry import InMemoryApiMethodRegistry


class StubHandler:
    async def execute(self, context, parameters):
        raise AssertionError("not called")


def definition(name: str = "order.get") -> ApiMethodDefinition:
    return ApiMethodDefinition(
        target=ApiMethodTarget(AppId("shop"), ApiMethodName(name)),
        allowed_methods=frozenset({ApiHttpMethod("GET")}),
        handler=StubHandler(),
    )


def test_registry_is_extended_by_registration_not_dispatch_branch() -> None:
    registry = InMemoryApiMethodRegistry()
    item = definition()

    registered = registry.register(item)
    duplicate = registry.register(item)
    resolved = registry.resolve(item.target)
    missing = registry.resolve(ApiMethodTarget(AppId("shop"), ApiMethodName("missing")))

    assert isinstance(registered, ApiMethodRegistered)
    assert isinstance(duplicate, ApiMethodRegistrationRejected)
    assert isinstance(resolved, ApiMethodResolved)
    assert resolved.definition is item
    assert isinstance(missing, ApiMethodMissing)


def test_registry_accepts_multiple_methods_without_central_branch_changes() -> None:
    registry = InMemoryApiMethodRegistry()
    first = definition("order.get")
    second = definition("product.search")
    registry.register(first)
    registry.register(second)

    assert registry.resolve(first.target).definition is first
    assert registry.resolve(second.target).definition is second
