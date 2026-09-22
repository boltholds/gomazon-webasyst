from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

from gomazon_webasyst.application.ports.installed_application_catalog import (
    InstalledApplicationCatalog,
)
from gomazon_webasyst.compatibility.webasyst.routing.backend_catalog import (
    BackendRoutesLoaded,
    FilesystemBackendRouteCatalog,
)
from gomazon_webasyst.compatibility.webasyst.routing.legacy_parser import (
    AppDispatchRule,
)


async def create_installed_backend_route_table(
    webasyst_root: Path,
    installed_applications: InstalledApplicationCatalog,
) -> Mapping[str, tuple[AppDispatchRule, ...]]:
    snapshot = await installed_applications.snapshot()
    source = FilesystemBackendRouteCatalog(webasyst_root)
    routes: dict[str, tuple[AppDispatchRule, ...]] = {}

    for application in snapshot.applications:
        resolution = source.resolve(application.app_id)
        if isinstance(resolution, BackendRoutesLoaded):
            routes[application.app_id.value] = resolution.routes

    return MappingProxyType(routes)
