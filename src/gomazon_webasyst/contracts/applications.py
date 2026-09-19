from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from gomazon_webasyst.application.app_values import AppId, PluginRef
from gomazon_webasyst.contracts.enums import (
    ApplicationHeaderAccessKind,
    ApplicationUiVersion,
    ExternalCalendarIntegrationLevel,
    PluginHandlerKind,
    PluginIntegrationKind,
)


ConfigScalar: TypeAlias = str | int | bool


class ApplicationCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    frontend: bool = False
    rights: bool = False
    plugins: bool = False
    auth: bool = False
    themes: bool = False
    pages: bool = False
    mobile: bool = False
    csrf: bool = False
    my_account: bool = False
    system: bool = False


class ApplicationRoutingParameter(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: Annotated[str, Field(min_length=1)]
    value: ConfigScalar


class PublicHeaderAccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[ApplicationHeaderAccessKind.PUBLIC] = (
        ApplicationHeaderAccessKind.PUBLIC
    )


class RequiresPermissionHeaderAccess(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[ApplicationHeaderAccessKind.REQUIRES_PERMISSION] = (
        ApplicationHeaderAccessKind.REQUIRES_PERMISSION
    )
    name: Annotated[str, Field(min_length=1)]


ApplicationHeaderAccess: TypeAlias = Annotated[
    PublicHeaderAccess | RequiresPermissionHeaderAccess,
    Field(discriminator="kind"),
]


class ApplicationHeaderItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: Annotated[str, Field(min_length=1)]
    name: Annotated[str, Field(min_length=1)]
    icon: str = ""
    link: str = ""
    access: ApplicationHeaderAccess = Field(default_factory=PublicHeaderAccess)


class ApplicationDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: AppId
    name: Annotated[str, Field(min_length=1)]
    version: str = ""
    vendor: str = ""
    description: str = ""
    icon: str = ""
    ui_versions: tuple[ApplicationUiVersion, ...] = ()
    capabilities: ApplicationCapabilities = Field(
        default_factory=ApplicationCapabilities
    )
    routing_parameters: tuple[ApplicationRoutingParameter, ...] = ()
    header_items: tuple[ApplicationHeaderItem, ...] = ()


class PluginCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    frontend: bool = False
    rights: bool = False
    custom_settings: bool = False
    site_settings: bool = False
    photos_settings: bool = False


class NoPluginIntegration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[PluginIntegrationKind.NONE] = PluginIntegrationKind.NONE


class ExternalCalendarIntegration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[PluginIntegrationKind.EXTERNAL_CALENDAR] = (
        PluginIntegrationKind.EXTERNAL_CALENDAR
    )
    level: ExternalCalendarIntegrationLevel


PluginIntegration: TypeAlias = Annotated[
    NoPluginIntegration | ExternalCalendarIntegration,
    Field(discriminator="kind"),
]


class OwnedAppHandler(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[PluginHandlerKind.OWNED_APP] = PluginHandlerKind.OWNED_APP
    event: Annotated[str, Field(min_length=1)]
    method: Annotated[str, Field(min_length=1)]


class CrossApplicationHandler(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[PluginHandlerKind.CROSS_APPLICATION] = (
        PluginHandlerKind.CROSS_APPLICATION
    )
    event_app_id: AppId
    event: Annotated[str, Field(min_length=1)]
    class_name: Annotated[str, Field(min_length=1)]
    method: Annotated[str, Field(min_length=1)]


PluginEventHandler: TypeAlias = Annotated[
    OwnedAppHandler | CrossApplicationHandler,
    Field(discriminator="kind"),
]


class PluginDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ref: PluginRef
    name: Annotated[str, Field(min_length=1)]
    description: str = ""
    version: str = ""
    vendor: str = ""
    icon: str = ""
    capabilities: PluginCapabilities = Field(default_factory=PluginCapabilities)
    integration: PluginIntegration = Field(default_factory=NoPluginIntegration)
    handlers: tuple[PluginEventHandler, ...] = ()
