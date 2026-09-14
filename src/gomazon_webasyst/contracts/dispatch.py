from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from gomazon_webasyst.contracts.enums import (
    DispatchNamespaceKind,
    DispatchRequestKind,
    DispatchTargetKind,
    HandlerRegistryLookupKind,
    LegacyDispatchOutcomeKind,
    PluginRegistryLookupKind,
)

from gomazon_webasyst.contracts.routing import RedirectSettlement, RouteData


class AppNamespace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[DispatchNamespaceKind.APP] = DispatchNamespaceKind.APP
    app: str


class PluginNamespace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[DispatchNamespaceKind.PLUGIN] = DispatchNamespaceKind.PLUGIN
    app: str
    plugin: str


DispatchNamespace: TypeAlias = Annotated[
    AppNamespace | PluginNamespace,
    Field(discriminator="kind"),
]


class DefaultDispatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[DispatchRequestKind.DEFAULT] = DispatchRequestKind.DEFAULT
    namespace: DispatchNamespace
    module: str


class ActionDispatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[DispatchRequestKind.ACTION] = DispatchRequestKind.ACTION
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
    kind: Literal[DispatchTargetKind.CONTROLLER] = DispatchTargetKind.CONTROLLER
    handler_id: str


class SingleActionTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[DispatchTargetKind.SINGLE_ACTION] = DispatchTargetKind.SINGLE_ACTION
    handler_id: str


class MultiActionTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[DispatchTargetKind.MULTI_ACTION] = DispatchTargetKind.MULTI_ACTION
    handler_id: str
    action_method: str


DispatchTarget: TypeAlias = Annotated[
    ControllerTarget | SingleActionTarget | MultiActionTarget,
    Field(discriminator="kind"),
]


class HandlerDispatchOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[LegacyDispatchOutcomeKind.HANDLER] = LegacyDispatchOutcomeKind.HANDLER
    dispatch: ResolvedDispatch
    target: DispatchTarget


LegacyDispatchOutcome: TypeAlias = Annotated[
    RedirectSettlement | HandlerDispatchOutcome,
    Field(discriminator="kind"),
]


class HandlerRegistered(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[HandlerRegistryLookupKind.REGISTERED] = HandlerRegistryLookupKind.REGISTERED
    handler_id: str


class HandlerMissing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[HandlerRegistryLookupKind.MISSING] = HandlerRegistryLookupKind.MISSING


HandlerRegistryLookup: TypeAlias = Annotated[
    HandlerRegistered | HandlerMissing,
    Field(discriminator="kind"),
]


class PluginAvailable(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[PluginRegistryLookupKind.AVAILABLE] = PluginRegistryLookupKind.AVAILABLE


class PluginMissing(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal[PluginRegistryLookupKind.MISSING] = PluginRegistryLookupKind.MISSING


PluginRegistryLookup: TypeAlias = Annotated[
    PluginAvailable | PluginMissing,
    Field(discriminator="kind"),
]
