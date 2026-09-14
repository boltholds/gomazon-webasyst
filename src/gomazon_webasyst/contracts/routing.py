from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, JsonValue


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
    kind: Literal["empty"] = "empty"


class ModuleSeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["module"] = "module"
    module: str


class ActionOnlySeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["action_only"] = "action_only"
    action: str


class ActionSeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["action"] = "action"
    module: str
    action: str


class PluginSeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["plugin"] = "plugin"
    plugin: str


class PluginActionOnlySeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["plugin_action_only"] = "plugin_action_only"
    plugin: str
    action: str


class PluginModuleSeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["plugin_module"] = "plugin_module"
    plugin: str
    module: str


class PluginActionSeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["plugin_action"] = "plugin_action"
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
    kind: Literal["any"] = "any"


class ModuleRouteConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["module"] = "module"
    module: str


AppRouteConstraint: TypeAlias = Annotated[
    AnyAppRouteConstraint | ModuleRouteConstraint,
    Field(discriminator="kind"),
]


class AppSettlement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["app"] = "app"
    app: str
    matched_prefix: str
    remaining_path: str
    seed: DispatchSeed
    constraint: AppRouteConstraint
    route_data: RouteData = Field(default_factory=dict)


class RedirectSettlement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["redirect"] = "redirect"
    location: str
    status_code: Literal[301, 302]


SettlementResolution: TypeAlias = Annotated[
    AppSettlement | RedirectSettlement,
    Field(discriminator="kind"),
]
