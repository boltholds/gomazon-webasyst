from dataclasses import dataclass

from gomazon_webasyst.application.api_execution.vo.method import ApiHttpMethod, ApiMethodTarget
from gomazon_webasyst.application.ports.api_methods import ApiMethodHandler


@dataclass(slots=True, frozen=True)
class ApiMethodDefinition:
    target: ApiMethodTarget
    allowed_methods: frozenset[ApiHttpMethod]
    handler: ApiMethodHandler

    def __post_init__(self) -> None:
        if not self.allowed_methods:
            raise ValueError("api method definition requires at least one allowed HTTP method")
