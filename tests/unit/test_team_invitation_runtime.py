from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_execution.vo.method import (
    ApiMethodName,
    ApiMethodTarget,
)
from gomazon_webasyst.composition.team import create_team_runtime_module
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
)
from gomazon_webasyst.application.application_registry.entities.installed_application import (
    InstalledApplication,
)
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


class NullPublisher:
    async def publish(self, request):
        from gomazon_webasyst.application.events.composites.contracts import (
            EventDispatchReport,
        )
        return EventDispatchReport(
            event=request.event,
            results=(),
            failures=(),
        )


def _app():
    return InstalledApplication(
        app_id=AppId("team"),
        display_name=ApplicationDisplayName("Team"),
        icons=ApplicationIconSet(()),
        vendor=ApplicationVendor("webasyst"),
        version=ApplicationVersion("2.3.4"),
        capabilities=ApplicationCapabilities(frozenset()),
        header_items=ApplicationHeaderItems(()),
    )


async def test_team_runtime_registers_users_invite_as_post_only() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    module = create_team_runtime_module(
        sessions,
        event_publisher=NullPublisher(),
        installed_applications=InMemoryInstalledApplicationCatalog((_app(),)),
        public_root_url="https://example.test/",
        server_timezone=timezone.utc,
    )

    methods = {item.target: item for item in module.api_methods}
    target = ApiMethodTarget(AppId("team"), ApiMethodName("users.invite"))
    assert target in methods
    assert {method.value for method in methods[target].allowed_methods} == {"POST"}
    await engine.dispose()
