from dataclasses import dataclass
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.access_values import AppId


@dataclass(slots=True, frozen=True)
class InstalledAppResolved:
    app_id: AppId


@dataclass(slots=True, frozen=True)
class InstalledAppMissing:
    app_id: AppId


InstalledAppResolution: TypeAlias = InstalledAppResolved | InstalledAppMissing


class InstalledAppDirectory(Protocol):
    async def resolve(self, app_id: AppId) -> InstalledAppResolution: ...
