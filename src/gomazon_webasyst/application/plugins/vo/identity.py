from dataclasses import dataclass

from gomazon_webasyst.application.access_values import AppId


@dataclass(slots=True, frozen=True)
class PluginId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("plugin id must not be empty")
        if len(self.value) > 64:
            raise ValueError("plugin id must not exceed 64 characters")


@dataclass(slots=True, frozen=True)
class PluginKey:
    app_id: AppId
    plugin_id: PluginId
