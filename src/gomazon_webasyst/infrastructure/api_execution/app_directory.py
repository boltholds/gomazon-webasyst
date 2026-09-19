from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.ports.installed_apps import (
    InstalledAppMissing,
    InstalledAppResolution,
    InstalledAppResolved,
)


class InMemoryInstalledAppDirectory:
    def __init__(self, app_ids: frozenset[AppId]) -> None:
        self._app_ids = app_ids

    async def resolve(self, app_id: AppId) -> InstalledAppResolution:
        if app_id not in self._app_ids:
            return InstalledAppMissing(app_id=app_id)
        return InstalledAppResolved(app_id=app_id)
