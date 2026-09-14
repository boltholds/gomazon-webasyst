from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from gomazon_webasyst.contracts.routing import RedirectSettlement, RouteData


class AppNamespace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["app"] = "app"
    app: str


class PluginNamespace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["plugin"] = "plugin"
    app: str
    plugin: str


DispatchNamespace: TypeAlias = Annotated[
    AppNamespace | PluginNamespace,
    Field(discriminator="kind"),
]


class DefaultDispatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["default"] = "default"
    namespace: DispatchNamespace
    module: str


class ActionDispatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["action"] = "action"
    namespace: DispatchNamespace
    module: str
    action: str


DispatchRequest: TypeAlias = Annotated[
    DefaultDispatch | ActionDispatch,
    Field(discriminator="kind"),
]


class ModuleHandlerKey(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    namespace: DispatchNamespace
    module: str


class ActionHandlerKey(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    namespace: DispatchNamespace
    module: str
    action: str


HandlerKey: TypeAlias = ModuleHandlerKey | ActionHandlerKey


class ResolvedDispatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    request: DispatchRequest
    route_data: RouteData = Field(default_factory=dict)


class ControllerTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["controller"] = "controller"
    handler_id: str


class SingleActionTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["single_action"] = "single_action"
    handler_id: str


class MultiActionTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["multi_action"] = "multi_action"
    handler_id: str
    action_method: str


DispatchTarget: TypeAlias = Annotated[
    ControllerTarget | SingleActionTarget | MultiActionTarget,
    Field(discriminator="kind"),
]


class HandlerDispatchOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["handler"] = "handler"
    dispatch: ResolvedDispatch
    target: DispatchTarget


LegacyDispatchOutcome: TypeAlias = Annotated[
    RedirectSettlement | HandlerDispatchOutcome,
    Field(discriminator="kind"),
]
