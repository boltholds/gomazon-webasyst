from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from gomazon_webasyst.contracts.enums import LegacyRouteRuleKind
from gomazon_webasyst.contracts.routing import (
    ActionOnlySeed,
    ActionSeed,
    DispatchSeed,
    EmptySeed,
    ModuleSeed,
    PluginActionOnlySeed,
    PluginActionSeed,
    PluginModuleSeed,
    PluginSeed,
    RouteData,
    RoutePattern,
)

from .errors import InvalidLegacyRoute
from .patterns import compile_route_pattern
from .seed_utils import seed_from_controls


_CONTROL_FIELDS = {
    "url",
    "app",
    "module",
    "action",
    "plugin",
    "redirect",
    "code",
    "disabled",
    "temporarily_off",
    "static_content",
    "static_content_type",
    "priority_settlement",
}


class SystemAppRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[LegacyRouteRuleKind.APP] = LegacyRouteRuleKind.APP
    pattern: RoutePattern
    app: str
    seed: DispatchSeed
    route_data: RouteData = Field(default_factory=dict)
    temporarily_off: bool = False


class SystemRedirectRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[LegacyRouteRuleKind.REDIRECT] = LegacyRouteRuleKind.REDIRECT
    pattern: RoutePattern
    location_template: str
    status_code: Literal[301, 302]
    disabled: bool = False
    temporarily_off: bool = False


SystemRouteRule: TypeAlias = Annotated[
    SystemAppRule | SystemRedirectRule,
    Field(discriminator="kind"),
]


class AppDispatchRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[LegacyRouteRuleKind.DISPATCH] = LegacyRouteRuleKind.DISPATCH
    pattern: RoutePattern
    app: str
    seed: DispatchSeed
    route_data: RouteData = Field(default_factory=dict)
    temporarily_off: bool = False


class SystemRouteTable(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    routes: dict[str, tuple[SystemRouteRule, ...]]
    aliases: dict[str, str] = Field(default_factory=dict)


RawRouteCollection: TypeAlias = Mapping[Any, Any] | Sequence[Any]


def _iter_route_entries(routes: RawRouteCollection) -> list[tuple[Any, Any]]:
    if isinstance(routes, Mapping):
        return list(routes.items())
    if isinstance(routes, Sequence) and not isinstance(routes, (str, bytes, bytearray)):
        return list(enumerate(routes))
    raise InvalidLegacyRoute("route collection must be a mapping or sequence")


def _route_mapping_base(route_id: Any, value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        route = dict(value)
        if "url" not in route:
            if isinstance(route_id, int):
                raise InvalidLegacyRoute("list route entries must define url")
            route["url"] = str(route_id)
        return route
    if not isinstance(value, str):
        raise InvalidLegacyRoute("route entry must be a mapping or shorthand string")
    if isinstance(route_id, int):
        raise InvalidLegacyRoute("shorthand route requires a string route key")
    return {"url": str(route_id), "__shorthand__": value}


def _system_route_mapping(route_id: Any, value: Any) -> dict[str, Any]:
    route = _route_mapping_base(route_id, value)
    if "__shorthand__" not in route:
        return route
    parts = str(route.pop("__shorthand__")).split("/")
    if not parts or not parts[0]:
        raise InvalidLegacyRoute("system shorthand route requires app id")
    route["app"] = parts[0]
    if len(parts) > 1 and parts[1]:
        route["module"] = parts[1]
    return route


def _app_route_mapping(app_id: str, route_id: Any, value: Any) -> dict[str, Any]:
    route = _route_mapping_base(route_id, value)
    if "__shorthand__" in route:
        parts = str(route.pop("__shorthand__")).split("/")
        if not parts or not parts[0]:
            raise InvalidLegacyRoute("app shorthand route requires module")
        route["module"] = parts[0]
        if len(parts) > 1 and parts[1]:
            route["action"] = parts[1]
    if not route.get("app"):
        route["app"] = app_id
    return route


def _seed_from_route(route: Mapping[str, Any]) -> DispatchSeed:
    controls: dict[str, str] = {}
    for name in ("module", "action", "plugin"):
        if name in route and route[name] not in (None, ""):
            controls[name] = str(route[name])
    return seed_from_controls(controls)


def _route_data(route: Mapping[str, Any]) -> RouteData:
    return {str(k): v for k, v in route.items() if k not in _CONTROL_FIELDS}


def _validate_supported(route: Mapping[str, Any]) -> None:
    if "static_content" in route:
        raise InvalidLegacyRoute("static_content routes are outside the routing foundation slice")
    if route.get("priority_settlement"):
        raise InvalidLegacyRoute("priority_settlement routes are outside the routing foundation slice")


def _parse_system_collection(routes: RawRouteCollection) -> tuple[SystemRouteRule, ...]:
    parsed: list[SystemRouteRule] = []
    for route_id, value in _iter_route_entries(routes):
        route = _system_route_mapping(route_id, value)
        _validate_supported(route)
        pattern = compile_route_pattern(str(route["url"]))
        temporarily_off = bool(route.get("temporarily_off"))

        if "redirect" in route:
            parsed.append(
                SystemRedirectRule(
                    pattern=pattern,
                    location_template=str(route["redirect"]),
                    status_code=302 if route.get("code") == 302 else 301,
                    disabled=bool(route.get("disabled")),
                    temporarily_off=temporarily_off,
                )
            )
            continue

        app = route.get("app")
        if not app:
            raise InvalidLegacyRoute("system dispatch route requires app")
        parsed.append(
            SystemAppRule(
                pattern=pattern,
                app=str(app),
                seed=_seed_from_route(route),
                route_data=_route_data(route),
                temporarily_off=temporarily_off,
            )
        )
    return tuple(parsed)


def parse_system_routes(raw: Mapping[str, Any]) -> SystemRouteTable:
    aliases: dict[str, str] = {}
    routes: dict[str, tuple[SystemRouteRule, ...]] = {}

    for domain, domain_routes in raw.items():
        if isinstance(domain_routes, str):
            aliases[str(domain)] = domain_routes
        else:
            routes[str(domain)] = _parse_system_collection(domain_routes)

    for alias, target in aliases.items():
        routes[alias] = routes.get(target, ())

    return SystemRouteTable(routes=routes, aliases=aliases)


def parse_app_routes(app: str, raw: RawRouteCollection) -> tuple[AppDispatchRule, ...]:
    parsed: list[AppDispatchRule] = []
    for route_id, value in _iter_route_entries(raw):
        route = _app_route_mapping(app, route_id, value)
        _validate_supported(route)
        if "redirect" in route:
            raise InvalidLegacyRoute("app-level redirect routes are outside this first slice")
        parsed.append(
            AppDispatchRule(
                pattern=compile_route_pattern(str(route["url"])),
                app=str(route["app"]),
                seed=_seed_from_route(route),
                route_data=_route_data(route),
                temporarily_off=bool(route.get("temporarily_off")),
            )
        )
    return tuple(parsed)
