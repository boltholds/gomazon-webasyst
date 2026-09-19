from gomazon_webasyst.application.app_values import AppId
from gomazon_webasyst.contracts.applications import (
    ApplicationCapabilities,
    ApplicationDescriptor,
)
from gomazon_webasyst.contracts.enums import ApplicationUiVersion


PHOTOS_APPLICATION = ApplicationDescriptor(
    id=AppId("photos"),
    name="Photos",
    icon="wa-apps/photos/img/photos.svg",
    version="2.3.0",
    vendor="webasyst",
    ui_versions=(ApplicationUiVersion.UI_2_0,),
    capabilities=ApplicationCapabilities(
        rights=True,
        frontend=True,
        auth=True,
        themes=True,
        plugins=True,
        pages=True,
        mobile=True,
        my_account=True,
    ),
)
