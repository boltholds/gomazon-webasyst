from gomazon_webasyst.application.app_values import AppId
from gomazon_webasyst.contracts.applications import ApplicationDescriptor
from gomazon_webasyst.contracts.enums import ApplicationUiVersion


APIEXPLORER_APPLICATION = ApplicationDescriptor(
    id=AppId("apiexplorer"),
    name="API Explorer",
    description="REST client for all API-enabled apps",
    icon="wa-apps/apiexplorer/img/apiexplorer.svg",
    version="1.1.1",
    vendor="webasyst",
    ui_versions=(ApplicationUiVersion.UI_2_0,),
)
