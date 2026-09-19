from pathlib import Path

import pytest

pytest.importorskip("aiosqlite")

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.events.composites.contracts import (
    EventDispatchRequest,
)
from gomazon_webasyst.application.events.entities.handler_definition import (
    EventHandlerDefinition,
)
from gomazon_webasyst.application.events.vo.identity import (
    EventHandlerId,
    EventKey,
    EventName,
)
from gomazon_webasyst.application.events.vo.owners import PluginEventOwner
from gomazon_webasyst.application.events.vo.patterns import (
    ExactEventPattern,
    ExactEventSource,
)
from gomazon_webasyst.application.events.vo.payload import (
    EventHandlerReturned,
    LegacyEventPayload,
)
from gomazon_webasyst.application.plugins.vo.identity import PluginId, PluginKey
from gomazon_webasyst.application.ports.installed_plugin_catalog import (
    InstalledPluginMissing,
    InstalledPluginResolved,
)
from gomazon_webasyst.application.runtime.entities.application_module import (
    ApplicationRuntimeModule,
)
from gomazon_webasyst.application.runtime.entities.plugin_module import (
    PluginRuntimeModule,
)
from gomazon_webasyst.compatibility.webasyst.application_registry.installer_policy import (
    NeverForceInstaller,
)
from gomazon_webasyst.composition.application_runtime import (
    ApplicationRuntimeInitializationError,
)
from gomazon_webasyst.composition.container import (
    create_container_with_runtime_catalogs,
)
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.contracts.enums import RuntimeLinkRejectReason
from gomazon_webasyst.infrastructure.application_registry.filesystem_catalog import (
    FilesystemInstalledApplicationCatalog,
)
from gomazon_webasyst.infrastructure.plugins.filesystem_catalog import (
    FilesystemInstalledPluginCatalog,
)


class PluginHandler:
    async def handle(self, context, payload):
        return EventHandlerReturned(
            value=LegacyEventPayload(value="python-plugin-result")
        )


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _root(tmp_path: Path, *, enabled: bool) -> Path:
    root = tmp_path / ("enabled" if enabled else "disabled")
    root.mkdir()
    _write(root, "wa-config/apps.php", "<?php return ['shop' => true];")
    _write(
        root,
        "wa-apps/shop/lib/config/app.php",
        "<?php return ['name' => 'Shop', 'vendor' => 'example'];",
    )
    _write(
        root,
        "wa-system/webasyst/lib/config/app.php",
        "<?php return ['name' => 'Webasyst', 'vendor' => 'webasyst'];",
    )
    enabled_php = "true" if enabled else "false"
    _write(
        root,
        "wa-config/apps/shop/plugins.php",
        f"<?php return ['reviews' => {enabled_php}];",
    )
    _write(
        root,
        "wa-apps/shop/plugins/reviews/lib/config/plugin.php",
        "<?php return ["
        "'name' => 'Reviews', "
        "'vendor' => 'example', "
        "'handlers' => ['order_saved' => 'legacyOrderSaved']"
        "];",
    )
    return root


async def _catalogs(root: Path):
    apps = FilesystemInstalledApplicationCatalog(
        root,
        installer_policy=NeverForceInstaller(),
    )
    plugins = FilesystemInstalledPluginCatalog(
        root,
        await apps.snapshot(),
    )
    return apps, plugins


def _runtime_module() -> ApplicationRuntimeModule:
    key = PluginKey(AppId("shop"), PluginId("reviews"))
    plugin = PluginRuntimeModule(
        key=key,
        dispatch_handlers=(),
        api_methods=(),
        event_handlers=(
            EventHandlerDefinition(
                handler_id=EventHandlerId("reviews-python-order-saved"),
                owner=PluginEventOwner(key),
                source=ExactEventSource(AppId("shop")),
                pattern=ExactEventPattern(EventName("order_saved")),
                handler=PluginHandler(),
            ),
        ),
    )
    return ApplicationRuntimeModule(
        app_id=AppId("shop"),
        dispatch_handlers=(),
        api_methods=(),
        event_handlers=(),
        plugins=(plugin,),
    )


@pytest.mark.asyncio
async def test_installed_plugin_manifest_is_metadata_not_executable_code(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, enabled=True)
    apps, plugins = await _catalogs(root)
    key = PluginKey(AppId("shop"), PluginId("reviews"))

    discovered = await plugins.resolve(key)
    assert isinstance(discovered, InstalledPluginResolved)
    assert (
        discovered.plugin.handler_declarations.items[0].methods[0].value
        == "legacyOrderSaved"
    )

    container = create_container_with_runtime_catalogs(
        Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            webasyst_root=root,
        ),
        installed_application_catalog=apps,
        installed_plugin_catalog=plugins,
        runtime_modules=(),
    )
    try:
        await container.initialize()
        report = await container.application_runtime.event_dispatcher.dispatch(
            EventDispatchRequest(
                event=EventKey(AppId("shop"), EventName("order_saved")),
                payload=LegacyEventPayload(value={"id": 7}),
            )
        )
        assert report.results == ()
    finally:
        await container.close()


@pytest.mark.asyncio
async def test_explicit_python_plugin_runtime_makes_handler_executable(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, enabled=True)
    apps, plugins = await _catalogs(root)
    container = create_container_with_runtime_catalogs(
        Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            webasyst_root=root,
        ),
        installed_application_catalog=apps,
        installed_plugin_catalog=plugins,
        runtime_modules=(_runtime_module(),),
    )
    try:
        await container.initialize()
        report = await container.application_runtime.event_dispatcher.dispatch(
            EventDispatchRequest(
                event=EventKey(AppId("shop"), EventName("order_saved")),
                payload=LegacyEventPayload(value={"id": 7}),
            )
        )
        assert tuple(result.value.value for result in report.results) == (
            "python-plugin-result",
        )
    finally:
        await container.close()


@pytest.mark.asyncio
async def test_disabled_plugin_rejects_python_runtime_module(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path, enabled=False)
    apps, plugins = await _catalogs(root)
    key = PluginKey(AppId("shop"), PluginId("reviews"))
    assert isinstance(await plugins.resolve(key), InstalledPluginMissing)

    container = create_container_with_runtime_catalogs(
        Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            webasyst_root=root,
        ),
        installed_application_catalog=apps,
        installed_plugin_catalog=plugins,
        runtime_modules=(_runtime_module(),),
    )
    try:
        with pytest.raises(ApplicationRuntimeInitializationError) as exc_info:
            await container.initialize()
        assert RuntimeLinkRejectReason.PLUGIN_NOT_INSTALLED in {
            issue.reason for issue in exc_info.value.rejected.issues
        }
    finally:
        await container.close()
