from dataclasses import dataclass

from gomazon_webasyst.application.access_values import AppId


@dataclass(slots=True, frozen=True)
class PluginHandlerEventPattern:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("plugin handler event pattern must not be empty")


@dataclass(slots=True, frozen=True)
class PluginHandlerMethodName:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("plugin handler method name must not be empty")


@dataclass(slots=True, frozen=True)
class PluginHandlerDeclaration:
    source_app_id: AppId
    event_pattern: PluginHandlerEventPattern
    methods: tuple[PluginHandlerMethodName, ...]

    def __post_init__(self) -> None:
        if not self.methods:
            raise ValueError("plugin handler declaration must contain a method")


@dataclass(slots=True, frozen=True)
class PluginHandlerDeclarations:
    items: tuple[PluginHandlerDeclaration, ...]
