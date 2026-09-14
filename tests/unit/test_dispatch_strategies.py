from gomazon_webasyst.compatibility.webasyst.dispatch.strategies import DispatchStrategyRegistry
from gomazon_webasyst.contracts.dispatch import (
    ActionDispatch,
    AppNamespace,
    ControllerTarget,
    PluginNamespace,
)


class FakeStrategy:
    def __init__(self, name: str) -> None:
        self.name = name

    def resolve(self, request, *, try_default=False):
        return ControllerTarget(handler_id=self.name)


def test_app_specific_strategy_overrides_default() -> None:
    default = FakeStrategy("default")
    custom = FakeStrategy("blog-custom")
    registry = DispatchStrategyRegistry(default)
    registry.register("blog", custom)

    blog = ActionDispatch(
        namespace=AppNamespace(app="blog"), module="frontend", action="post"
    )
    site = ActionDispatch(
        namespace=AppNamespace(app="site"), module="frontend", action="page"
    )

    assert registry.for_request(blog) is custom
    assert registry.for_request(site) is default


def test_plugin_namespace_uses_strategy_of_owning_app() -> None:
    default = FakeStrategy("default")
    custom = FakeStrategy("shop-custom")
    registry = DispatchStrategyRegistry(default)
    registry.register("shop", custom)

    request = ActionDispatch(
        namespace=PluginNamespace(app="shop", plugin="reviews"),
        module="frontend",
        action="list",
    )
    assert registry.for_request(request) is custom
