from gomazon_webasyst.application.app_values import AppId
from gomazon_webasyst.contracts.applications import (
    ApplicationCapabilities,
    ApplicationDescriptor,
)
from gomazon_webasyst.contracts.enums import ApplicationUiVersion


DEVELOPER_APPLICATION = ApplicationDescriptor(
    id=AppId("developer"),
    name="Developer",
    icon="wa-apps/developer/img/developer.png",
    version="1.1.1",
    vendor="webasyst",
    ui_versions=(ApplicationUiVersion.LEGACY_1_3,),
    capabilities=ApplicationCapabilities(
        plugins=True,
        csrf=True,
    ),
)
