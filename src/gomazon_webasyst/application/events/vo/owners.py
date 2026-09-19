from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.plugins.vo.identity import PluginKey


@dataclass(slots=True, frozen=True)
class ApplicationEventOwner:
    app_id: AppId


@dataclass(slots=True, frozen=True)
class PluginEventOwner:
    key: PluginKey


EventHandlerOwner: TypeAlias = ApplicationEventOwner | PluginEventOwner
