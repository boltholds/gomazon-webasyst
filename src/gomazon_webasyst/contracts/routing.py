from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from gomazon_webasyst.contracts.enums import (
    AppRouteConstraintKind,
    DispatchSeedKind,
    SettlementKind,
)


RouteData: TypeAlias = dict[str, JsonValue]


class FrontendRouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    domain: str
    path: str
    query: dict[str, str] = Field(default_factory=dict)


class BackendRouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    app: str
    path: str
    query: dict[str, str] = Field(default_factory=dict)


class RouteCapture(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    regex: str


class RoutePattern(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str
    regex_source: str
    captures: tuple[RouteCapture, ...] = ()


class EmptySeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[DispatchSeedKind.EMPTY] = DispatchSeedKind.EMPTY


class ModuleSeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[DispatchSeedKind.MODULE] = DispatchSeedKind.MODULE
    module: str


class ActionOnlySeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[DispatchSeedKind.ACTION_ONLY] = DispatchSeedKind.ACTION_ONLY
    action: str


class ActionSeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[DispatchSeedKind.ACTION] = DispatchSeedKind.ACTION
    module: str
    action: str


class PluginSeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[DispatchSeedKind.PLUGIN] = DispatchSeedKind.PLUGIN
    plugin: str


class PluginActionOnlySeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[DispatchSeedKind.PLUGIN_ACTION_ONLY] = DispatchSeedKind.PLUGIN_ACTION_ONLY
    plugin: str
    action: str


class PluginModuleSeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[DispatchSeedKind.PLUGIN_MODULE] = DispatchSeedKind.PLUGIN_MODULE
    plugin: str
    module: str


class PluginActionSeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[DispatchSeedKind.PLUGIN_ACTION] = DispatchSeedKind.PLUGIN_ACTION
    plugin: str
    module: str
    action: str


DispatchSeed: TypeAlias = Annotated[
    EmptySeed
    | ModuleSeed
    | ActionOnlySeed
    | ActionSeed
    | PluginSeed
    | PluginActionOnlySeed
    | PluginModuleSeed
    | PluginActionSeed,
    Field(discriminator="kind"),
]


class AnyAppRouteConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[AppRouteConstraintKind.ANY] = AppRouteConstraintKind.ANY


class ModuleRouteConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[AppRouteConstraintKind.MODULE] = AppRouteConstraintKind.MODULE
    module: str


AppRouteConstraint: TypeAlias = Annotated[
    AnyAppRouteConstraint | ModuleRouteConstraint,
    Field(discriminator="kind"),
]


class AppSettlement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[SettlementKind.APP] = SettlementKind.APP
    app: str
    matched_prefix: str
    remaining_path: str
    seed: DispatchSeed
    constraint: AppRouteConstraint
    route_data: RouteData = Field(default_factory=dict)


class RedirectSettlement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[SettlementKind.REDIRECT] = SettlementKind.REDIRECT
    location: str
    status_code: Literal[301, 302]


SettlementResolution: TypeAlias = Annotated[
    AppSettlement | RedirectSettlement,
    Field(discriminator="kind"),
]
