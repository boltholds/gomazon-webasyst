from gomazon_webasyst.application.ports.installed_application_catalog import (
    InstalledApplicationCatalog,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.installer_policy import (
    NeverForceInstaller,
)
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.infrastructure.application_registry.filesystem_catalog import (
    FilesystemInstalledApplicationCatalog,
)


def create_installed_application_catalog(
    settings: Settings,
) -> InstalledApplicationCatalog:
    return FilesystemInstalledApplicationCatalog(
        settings.webasyst_root,
        installer_policy=NeverForceInstaller(),
    )
