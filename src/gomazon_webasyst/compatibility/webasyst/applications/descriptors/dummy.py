from gomazon_webasyst.application.app_values import AppId
from gomazon_webasyst.contracts.applications import (
    ApplicationCapabilities,
    ApplicationDescriptor,
)
from gomazon_webasyst.contracts.enums import ApplicationUiVersion


DUMMY_APPLICATION = ApplicationDescriptor(
    id=AppId("dummy"),
    name="Dummy",
    icon="wa-apps/dummy/img/dummy.png",
    version="0.2.0",
    vendor="webasyst",
    ui_versions=(ApplicationUiVersion.UI_2_0,),
    capabilities=ApplicationCapabilities(
        rights=True,
        frontend=True,
    ),
)
