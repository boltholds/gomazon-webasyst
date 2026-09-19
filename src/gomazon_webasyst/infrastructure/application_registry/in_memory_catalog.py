from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.application_registry.entities.installed_application import (
    InstalledApplication,
)
from gomazon_webasyst.application.ports.installed_application_catalog import (
    InstalledApplicationMissing,
    InstalledApplicationResolution,
    InstalledApplicationResolved,
    InstalledApplicationSnapshot,
)


class InMemoryInstalledApplicationCatalog:
    def __init__(
        self,
        applications: tuple[InstalledApplication, ...],
    ) -> None:
        by_id: dict[AppId, InstalledApplication] = {}
        for application in applications:
            if application.app_id in by_id:
                raise ValueError(
                    f"duplicate installed application id: {application.app_id.value}"
                )
            by_id[application.app_id] = application

        self._applications = by_id
        self._ordered = applications

    async def resolve(self, app_id: AppId) -> InstalledApplicationResolution:
        if app_id not in self._applications:
            return InstalledApplicationMissing(app_id)
        return InstalledApplicationResolved(self._applications[app_id])

    async def snapshot(self) -> InstalledApplicationSnapshot:
        return InstalledApplicationSnapshot(self._ordered)
