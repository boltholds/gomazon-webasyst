import pytest

from gomazon_webasyst.compatibility.webasyst.routing.backend_resolver import BackendRouteResolver
from gomazon_webasyst.compatibility.webasyst.routing.errors import InvalidDispatchParameter
from gomazon_webasyst.contracts.dispatch import ActionDispatch, AppNamespace, DefaultDispatch, PluginNamespace
from gomazon_webasyst.contracts.routing import (
    ActionOnlySeed,
    ActionSeed,
    BackendRouteRequest,
    ModuleSeed,
    PluginSeed,
)


resolver = BackendRouteResolver()


def test_backend_module_defaults_to_backend() -> None:
    result = resolver.resolve(BackendRouteRequest(app="team", path="", query={}))
    assert result.request == DefaultDispatch(
        namespace=AppNamespace(app="team"), module="backend"
    )


def test_query_can_supply_module_and_action() -> None:
    result = resolver.resolve(
        BackendRouteRequest(
            app="team", path="", query={"module": "users", "action": "list"}
        )
    )
    assert result.request == ActionDispatch(
        namespace=AppNamespace(app="team"), module="users", action="list"
    )


def test_route_seed_overrides_query_module_and_action() -> None:
    result = resolver.resolve(
        BackendRouteRequest(
            app="team", path="", query={"module": "users", "action": "list"}
        ),
        ActionSeed(module="settings", action="save"),
    )
    assert result.request == ActionDispatch(
        namespace=AppNamespace(app="team"), module="settings", action="save"
    )


def test_route_module_without_action_keeps_query_action() -> None:
    result = resolver.resolve(
        BackendRouteRequest(app="team", path="", query={"action": "list"}),
        ModuleSeed(module="users"),
    )
    assert result.request == ActionDispatch(
        namespace=AppNamespace(app="team"), module="users", action="list"
    )


def test_route_action_without_module_keeps_query_module() -> None:
    result = resolver.resolve(
        BackendRouteRequest(app="team", path="", query={"module": "users"}),
        ActionOnlySeed(action="edit"),
    )
    assert result.request == ActionDispatch(
        namespace=AppNamespace(app="team"), module="users", action="edit"
    )


def test_route_plugin_overrides_query_plugin_but_keeps_other_query_parts() -> None:
    result = resolver.resolve(
        BackendRouteRequest(
            app="shop",
            path="",
            query={"plugin": "old", "module": "orders", "action": "list"},
        ),
        PluginSeed(plugin="reviews"),
    )
    assert result.request == ActionDispatch(
        namespace=PluginNamespace(app="shop", plugin="reviews"),
        module="orders",
        action="list",
    )


def test_invalid_dispatch_identifier_raises_typed_400_error() -> None:
    with pytest.raises(InvalidDispatchParameter):
        resolver.resolve(
            BackendRouteRequest(app="team", path="", query={"module": "../users"})
        )


def test_route_data_is_preserved_separately_from_dispatch_controls() -> None:
    result = resolver.resolve(
        BackendRouteRequest(app="team", path="", query={}),
        route_data={"locale": "en_US"},
    )
    assert result.route_data == {"locale": "en_US"}
