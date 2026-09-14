from pydantic import TypeAdapter

from gomazon_webasyst.contracts.dispatch import DispatchNamespace
from gomazon_webasyst.contracts.enums import (
    DispatchNamespaceKind,
    EnumStr,
    SettlementKind,
)
from gomazon_webasyst.contracts.routing import (
    AppSettlement,
    AnyAppRouteConstraint,
    EmptySeed,
    SettlementResolution,
)


def test_discriminator_enums_share_enumstr_base() -> None:
    assert issubclass(SettlementKind, EnumStr)
    assert issubclass(DispatchNamespaceKind, EnumStr)


def test_model_kind_is_enum_member_and_json_stays_legacy_string() -> None:
    settlement = AppSettlement(
        app="blog",
        matched_prefix="",
        remaining_path="",
        seed=EmptySeed(),
        constraint=AnyAppRouteConstraint(),
    )

    assert settlement.kind is SettlementKind.APP
    assert settlement.model_dump(mode="json")["kind"] == "app"


def test_discriminated_unions_accept_raw_string_values() -> None:
    settlement = TypeAdapter(SettlementResolution).validate_python(
        {
            "kind": "app",
            "app": "blog",
            "matched_prefix": "",
            "remaining_path": "",
            "seed": {"kind": "empty"},
            "constraint": {"kind": "any"},
            "route_data": {},
        }
    )
    namespace = TypeAdapter(DispatchNamespace).validate_python(
        {"kind": "plugin", "app": "shop", "plugin": "reviews"}
    )

    assert settlement.kind is SettlementKind.APP
    assert namespace.kind is DispatchNamespaceKind.PLUGIN
