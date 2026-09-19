from gomazon_webasyst.application.app_values import AppId
from gomazon_webasyst.contracts.applications import (
    ApplicationCapabilities,
    ApplicationDescriptor,
    ApplicationRoutingParameter,
)
from gomazon_webasyst.contracts.enums import ApplicationUiVersion


BLOG_APPLICATION = ApplicationDescriptor(
    id=AppId("blog"),
    name="Blog",
    icon="wa-apps/blog/img/blog.svg",
    version="2.1.1",
    vendor="webasyst",
    ui_versions=(
        ApplicationUiVersion.LEGACY_1_3,
        ApplicationUiVersion.UI_2_0,
    ),
    capabilities=ApplicationCapabilities(
        rights=True,
        frontend=True,
        auth=True,
        themes=True,
        plugins=True,
        pages=True,
        mobile=True,
        csrf=True,
        my_account=True,
    ),
    routing_parameters=(
        ApplicationRoutingParameter(name="blog_url_type", value=1),
    ),
)
