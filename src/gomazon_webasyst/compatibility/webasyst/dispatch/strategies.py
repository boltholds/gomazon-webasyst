from typing import Protocol

from gomazon_webasyst.contracts.dispatch import DispatchRequest, DispatchTarget


class DispatchStrategy(Protocol):
    def resolve(
        self, request: DispatchRequest, *, try_default: bool = False
    ) -> DispatchTarget: ...


class DispatchStrategyRegistry:
    def __init__(self, default_strategy: DispatchStrategy):
        self._default = default_strategy
        self._overrides: dict[str, DispatchStrategy] = {}

    def register(self, app: str, strategy: DispatchStrategy) -> None:
        self._overrides[app] = strategy

    def for_request(self, request: DispatchRequest) -> DispatchStrategy:
        app = request.namespace.app
        return self._overrides.get(app, self._default)
