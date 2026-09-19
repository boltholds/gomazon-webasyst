from dataclasses import dataclass, field
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.app_values import AppId, PluginRef
from gomazon_webasyst.contracts.applications import (
    ApplicationDescriptor,
    PluginDescriptor,
)
from gomazon_webasyst.contracts.enums import (
    ApplicationResolutionKind,
    PluginListResultKind,
    PluginResolutionKind,
)


@dataclass(slots=True, frozen=True)
class ApplicationEnabled:
    descriptor: ApplicationDescriptor
    kind: ApplicationResolutionKind = field(
        default=ApplicationResolutionKind.ENABLED,
        init=False,
    )


@dataclass(slots=True, frozen=True)
class ApplicationDisabled:
    descriptor: ApplicationDescriptor
    kind: ApplicationResolutionKind = field(
        default=ApplicationResolutionKind.DISABLED,
        init=False,
    )


@dataclass(slots=True, frozen=True)
class ApplicationUnknown:
    app_id: AppId
    kind: ApplicationResolutionKind = field(
        default=ApplicationResolutionKind.UNKNOWN,
        init=False,
    )


ApplicationResolution: TypeAlias = (
    ApplicationEnabled | ApplicationDisabled | ApplicationUnknown
)


@dataclass(slots=True, frozen=True)
class PluginEnabled:
    descriptor: PluginDescriptor
    kind: PluginResolutionKind = field(
        default=PluginResolutionKind.ENABLED,
        init=False,
    )


@dataclass(slots=True, frozen=True)
class PluginDisabled:
    descriptor: PluginDescriptor
    kind: PluginResolutionKind = field(
        default=PluginResolutionKind.DISABLED,
        init=False,
    )


@dataclass(slots=True, frozen=True)
class PluginOwnerDisabled:
    descriptor: PluginDescriptor
    owner: ApplicationDescriptor
    kind: PluginResolutionKind = field(
        default=PluginResolutionKind.OWNER_DISABLED,
        init=False,
    )


@dataclass(slots=True, frozen=True)
class PluginUnknown:
    plugin_ref: PluginRef
    kind: PluginResolutionKind = field(
        default=PluginResolutionKind.UNKNOWN,
        init=False,
    )


PluginResolution: TypeAlias = (
    PluginEnabled | PluginDisabled | PluginOwnerDisabled | PluginUnknown
)


@dataclass(slots=True, frozen=True)
class PluginListResolved:
    app_id: AppId
    plugins: tuple[PluginDescriptor, ...]
    kind: PluginListResultKind = field(
        default=PluginListResultKind.LISTED,
        init=False,
    )


@dataclass(slots=True, frozen=True)
class PluginListOwnerDisabled:
    app_id: AppId
    kind: PluginListResultKind = field(
        default=PluginListResultKind.OWNER_DISABLED,
        init=False,
    )


@dataclass(slots=True, frozen=True)
class PluginListOwnerUnknown:
    app_id: AppId
    kind: PluginListResultKind = field(
        default=PluginListResultKind.OWNER_UNKNOWN,
        init=False,
    )


PluginListResult: TypeAlias = (
    PluginListResolved | PluginListOwnerDisabled | PluginListOwnerUnknown
)


class ApplicationRegistry(Protocol):
    def resolve_app(self, app_id: AppId) -> ApplicationResolution: ...

    def resolve_plugin(self, plugin_ref: PluginRef) -> PluginResolution: ...

    def list_catalog_apps(self) -> tuple[ApplicationDescriptor, ...]: ...

    def list_enabled_apps(self) -> tuple[ApplicationDescriptor, ...]: ...

    def list_enabled_apps_including_system(
        self,
    ) -> tuple[ApplicationDescriptor, ...]: ...

    def list_plugins(self, app_id: AppId) -> PluginListResult: ...

    def list_enabled_plugins(self, app_id: AppId) -> PluginListResult: ...
