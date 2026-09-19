from dataclasses import dataclass, field
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.application_registry.entities.installed_application import (
    InstalledApplication,
)
from gomazon_webasyst.contracts.enums import InstalledApplicationLookupKind


@dataclass(slots=True, frozen=True)
class InstalledApplicationResolved:
    application: InstalledApplication
    kind: InstalledApplicationLookupKind = field(
        init=False,
        default=InstalledApplicationLookupKind.RESOLVED,
    )


@dataclass(slots=True, frozen=True)
class InstalledApplicationMissing:
    app_id: AppId
    kind: InstalledApplicationLookupKind = field(
        init=False,
        default=InstalledApplicationLookupKind.MISSING,
    )


InstalledApplicationResolution: TypeAlias = (
    InstalledApplicationResolved | InstalledApplicationMissing
)


@dataclass(slots=True, frozen=True)
class InstalledApplicationSnapshot:
    applications: tuple[InstalledApplication, ...]

    def __post_init__(self) -> None:
        app_ids = [application.app_id for application in self.applications]
        if len(app_ids) != len(set(app_ids)):
            raise ValueError("duplicate installed application id")


class InstalledApplicationCatalog(Protocol):
    async def resolve(self, app_id: AppId) -> InstalledApplicationResolution: ...

    async def snapshot(self) -> InstalledApplicationSnapshot: ...
