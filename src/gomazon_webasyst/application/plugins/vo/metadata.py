from dataclasses import dataclass, field
from typing import TypeAlias

from gomazon_webasyst.contracts.enums import PluginImageKind


@dataclass(slots=True, frozen=True)
class PluginDisplayName:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("plugin display name must not be empty")


@dataclass(slots=True, frozen=True)
class PluginVendor:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("plugin vendor must not be empty")


@dataclass(slots=True, frozen=True)
class PluginVersion:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("plugin version must not be empty")


@dataclass(slots=True, frozen=True)
class PluginImageReference:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("plugin image reference must not be empty")


@dataclass(slots=True, frozen=True)
class PluginImagePresent:
    reference: PluginImageReference
    kind: PluginImageKind = field(init=False, default=PluginImageKind.PRESENT)


@dataclass(slots=True, frozen=True)
class PluginImageMissing:
    kind: PluginImageKind = field(init=False, default=PluginImageKind.MISSING)


PluginImageState: TypeAlias = PluginImagePresent | PluginImageMissing
