import pytest
from pydantic import TypeAdapter, ValidationError

from gomazon_webasyst.contracts.dispatch import (
    ActionDispatch,
    AppNamespace,
    DispatchRequest,
    PluginNamespace,
)
from gomazon_webasyst.contracts.routing import (
    DispatchSeed,
    RedirectSettlement,
    SettlementResolution,
)


def test_dispatch_request_is_discriminated_union() -> None:
    adapter = TypeAdapter(DispatchRequest)
    value = adapter.validate_python(
        {
            "kind": "action",
            "namespace": {"kind": "app", "app": "blog"},
            "module": "frontend",
            "action": "post",
        }
    )
    assert isinstance(value, ActionDispatch)
    assert isinstance(value.namespace, AppNamespace)


def test_plugin_namespace_requires_plugin() -> None:
    with pytest.raises(ValidationError):
        PluginNamespace(kind="plugin", app="shop")


def test_settlement_variants_do_not_share_nullable_control_fields() -> None:
    adapter = TypeAdapter(SettlementResolution)
    redirect = adapter.validate_python(
        {
            "kind": "redirect",
            "location": "/new/",
            "status_code": 301,
        }
    )
    assert isinstance(redirect, RedirectSettlement)
    assert not hasattr(redirect, "app")


def test_dispatch_seed_rejects_partial_action_state() -> None:
    adapter = TypeAdapter(DispatchSeed)
    with pytest.raises(ValidationError):
        adapter.validate_python({"kind": "action", "module": "frontend"})


def test_dispatch_seed_represents_action_without_module_explicitly() -> None:
    from gomazon_webasyst.contracts.routing import ActionOnlySeed

    seed = ActionOnlySeed(action="show")
    assert seed.kind == "action_only"
    assert not hasattr(seed, "module")


def test_dispatch_seed_represents_plugin_without_module_explicitly() -> None:
    from gomazon_webasyst.contracts.routing import PluginSeed

    seed = PluginSeed(plugin="reviews")
    assert seed.kind == "plugin"
    assert not hasattr(seed, "module")


def test_app_settlement_carries_route_constraint_as_variant() -> None:
    from gomazon_webasyst.contracts.routing import AppSettlement, EmptySeed, ModuleRouteConstraint

    settlement = AppSettlement(
        app="blog",
        matched_prefix="blog/",
        remaining_path="",
        seed=EmptySeed(),
        constraint=ModuleRouteConstraint(module="frontend"),
    )
    assert settlement.constraint.kind == "module"
    assert settlement.constraint.module == "frontend"


def test_resolved_dispatch_keeps_dynamic_route_data_outside_control_state() -> None:
    from gomazon_webasyst.contracts.dispatch import DefaultDispatch, ResolvedDispatch

    result = ResolvedDispatch(
        request=DefaultDispatch(namespace=AppNamespace(app="site"), module="frontend"),
        route_data={"locale": "en_US", "page": 4},
    )
    assert result.request.module == "frontend"
    assert result.route_data == {"locale": "en_US", "page": 4}


def test_legacy_outcome_is_discriminated_between_redirect_and_handler_dispatch() -> None:
    from pydantic import TypeAdapter
    from gomazon_webasyst.contracts.dispatch import HandlerDispatchOutcome, LegacyDispatchOutcome
    from gomazon_webasyst.contracts.routing import RedirectSettlement

    adapter = TypeAdapter(LegacyDispatchOutcome)
    redirect = adapter.validate_python({
        "kind": "redirect",
        "location": "/new/",
        "status_code": 301,
    })
    assert isinstance(redirect, RedirectSettlement)
    assert not isinstance(redirect, HandlerDispatchOutcome)
