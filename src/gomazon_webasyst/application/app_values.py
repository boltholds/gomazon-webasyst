from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class AppId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("app id must not be empty")
        if len(self.value) > 32:
            raise ValueError("app id must not exceed 32 characters")


@dataclass(slots=True, frozen=True)
class PluginId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("plugin id must not be empty")
        if len(self.value) > 64:
            raise ValueError("plugin id must not exceed 64 characters")


@dataclass(slots=True, frozen=True)
class PluginRef:
    app_id: AppId
    plugin_id: PluginId
