from gomazon_webasyst.application.app_values import AppId
from gomazon_webasyst.contracts.applications import (
    ApplicationCapabilities,
    ApplicationDescriptor,
)
from gomazon_webasyst.contracts.enums import ApplicationUiVersion


INSTALLER_APPLICATION = ApplicationDescriptor(
    id=AppId("installer"),
    name="Installer",
    description="Install new apps from the Webasyst Store",
    icon="wa-apps/installer/img/installer.svg",
    version="4.2.0",
    vendor="webasyst",
    ui_versions=(ApplicationUiVersion.UI_2_0,),
    capabilities=ApplicationCapabilities(
        system=True,
        csrf=True,
    ),
)
