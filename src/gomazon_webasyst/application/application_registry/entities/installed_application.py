from dataclasses import dataclass

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.application_registry.vo.capabilities import (
    ApplicationCapabilities,
)
from gomazon_webasyst.application.application_registry.vo.header_items import (
    ApplicationHeaderItems,
)
from gomazon_webasyst.application.application_registry.vo.icons import (
    ApplicationIconSet,
)
from gomazon_webasyst.application.application_registry.vo.metadata import (
    ApplicationDisplayName,
    ApplicationVendor,
    ApplicationVersion,
)


@dataclass(slots=True, frozen=True)
class InstalledApplication:
    app_id: AppId
    display_name: ApplicationDisplayName
    icons: ApplicationIconSet
    vendor: ApplicationVendor
    version: ApplicationVersion
    capabilities: ApplicationCapabilities
    header_items: ApplicationHeaderItems
