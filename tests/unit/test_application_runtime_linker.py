import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_execution.entities.method_definition import (
    ApiMethodDefinition,
)
from gomazon_webasyst.application.api_execution.vo.method import (
    ApiHttpMethod,
    ApiMethodName,
    ApiMethodTarget,
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
from gomazon_webasyst.application.events.entities.handler_definition import (
    EventHandlerDefinition,
)
from gomazon_webasyst.application.events.services.pattern_matcher import (
    EventPatternMatcher,
    EventPatternNotMatched,
)
from gomazon_webasyst.application.events.vo.identity import (
    EventHandlerId,
    EventKey,
    EventName,
)
from gomazon_webasyst.application.events.vo.owners import (
    ApplicationEventOwner,
    PluginEventOwner,
)
from gomazon_webasyst.application.events.vo.patterns import (
    ExactEventPattern,
    ExactEventSource,
)
from gomazon_webasyst.application.events.vo.payload import EventHandlerNoResult
from gomazon_webasyst.application.plugins.entities.installed_plugin import (
    InstalledPlugin,
)
from gomazon_webasyst.application.plugins.vo.capabilities import PluginCapabilities
from gomazon_webasyst.application.plugins.vo.handlers import PluginHandlerDeclarations
from gomazon_webasyst.application.plugins.vo.identity import PluginId, PluginKey
from gomazon_webasyst.application.plugins.vo.metadata import (
    PluginDisplayName,
    PluginImageMissing,
    PluginVendor,
    PluginVersion,
)
from gomazon_webasyst.application.runtime.composites.linker import (
    ApplicationRuntimeLinker,
)
from gomazon_webasyst.application.runtime.composites.results import (
    RuntimeLinkRejected,
    RuntimeLinkSucceeded,
)
from gomazon_webasyst.application.runtime.entities.application_module import (
    ApplicationRuntimeModule,
)
from gomazon_webasyst.application.runtime.entities.plugin_module import (
    PluginRuntimeModule,
)
from gomazon_webasyst.application.runtime.vo.dispatch import (
    ActionDispatchDefinition,
    DispatchHandlerId,
    PluginAvailabilityDefinition,
)
from gomazon_webasyst.compatibility.webasyst.dispatch.registry import (
    InMemoryDispatchRegistry,
)
from gomazon_webasyst.contracts.dispatch import (
    ActionHandlerKey,
    AppNamespace,
    HandlerMissing,
    HandlerRegistered,
    PluginAvailable,
    PluginNamespace,
)
from gomazon_webasyst.contracts.enums import RuntimeLinkRejectReason
from gomazon_webasyst.infrastructure.api_execution.method_registry import (
    InMemoryApiMethodRegistry,
)
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
)
from gomazon_webasyst.infrastructure.events.registry import (
    InMemoryEventHandlerRegistry,
)
from gomazon_webasyst.infrastructure.plugins.in_memory_catalog import (
    InMemoryInstalledPluginCatalog,
)


class ApiHandler:
    async def execute(self, context, parameters):
        raise AssertionError("not executed")


class EventHandler:
    async def handle(self, context, payload):
        return EventHandlerNoResult()


class RejectRegex:
    def match(self, expression, event_name):
        return EventPatternNotMatched()


def _installed_app(app_id: str) -> InstalledApplication:
    return InstalledApplication(
        app_id=AppId(app_id),
        display_name=ApplicationDisplayName(app_id.title()),
        icons=ApplicationIconSet(()),
        vendor=ApplicationVendor("example"),
        version=ApplicationVersion("1.0.0"),
        capabilities=ApplicationCapabilities(frozenset()),
        header_items=ApplicationHeaderItems(()),
    )


def _installed_plugin(app_id: str, plugin_id: str) -> InstalledPlugin:
    return InstalledPlugin(
        key=PluginKey(AppId(app_id), PluginId(plugin_id)),
        display_name=PluginDisplayName(plugin_id.title()),
        version=PluginVersion("1.0.0"),
        vendor=PluginVendor("example"),
        image=PluginImageMissing(),
        capabilities=PluginCapabilities(frozenset()),
        handler_declarations=PluginHandlerDeclarations(()),
    )


def _api(app_id: str, name: str = "ping") -> ApiMethodDefinition:
    return ApiMethodDefinition(
        target=ApiMethodTarget(AppId(app_id), ApiMethodName(name)),
        allowed_methods=frozenset({ApiHttpMethod("GET")}),
        handler=ApiHandler(),
    )


def _event(
    handler_id: str,
    *,
    owner,
    source_app: str = "shop",
) -> EventHandlerDefinition:
    return EventHandlerDefinition(
        handler_id=EventHandlerId(handler_id),
        owner=owner,
        source=ExactEventSource(AppId(source_app)),
        pattern=ExactEventPattern(EventName("saved")),
        handler=EventHandler(),
    )


def _linker(
    *,
    apps=("shop",),
    plugins=(),
):
    api = InMemoryApiMethodRegistry()
    dispatch = InMemoryDispatchRegistry()
    events = InMemoryEventHandlerRegistry(EventPatternMatcher(RejectRegex()))
    linker = ApplicationRuntimeLinker(
        installed_applications=InMemoryInstalledApplicationCatalog(
            tuple(_installed_app(app) for app in apps)
        ),
        installed_plugins=InMemoryInstalledPluginCatalog(
            tuple(_installed_plugin(app, plugin) for app, plugin in plugins)
        ),
        api_methods=api,
        dispatch=dispatch,
        events=events,
    )
    return linker, api, dispatch, events


@pytest.mark.asyncio
async def test_installed_application_links_api_dispatch_and_event_contributions() -> None:
    linker, api, dispatch, events = _linker()
    dispatch_key = ActionHandlerKey(
        namespace=AppNamespace(app="shop"),
        module="backend",
        action="index",
    )
    event = _event(
        "shop-saved",
        owner=ApplicationEventOwner(AppId("shop")),
    )
    module = ApplicationRuntimeModule(
        app_id=AppId("shop"),
        dispatch_handlers=(
            ActionDispatchDefinition(
                dispatch_key,
                DispatchHandlerId("shop-index"),
            ),
        ),
        api_methods=(_api("shop"),),
        event_handlers=(event,),
        plugins=(),
    )

    result = await linker.link((module,))

    assert isinstance(result, RuntimeLinkSucceeded)
    assert api.resolve(_api("shop").target).definition.target == _api("shop").target
    assert dispatch.action_id(dispatch_key) == HandlerRegistered(
        handler_id="shop-index"
    )
    matched = events.matching(EventKey(AppId("shop"), EventName("saved")))
    assert tuple(item.handler_id for item in matched.definitions) == (
        EventHandlerId("shop-saved"),
    )


@pytest.mark.asyncio
async def test_uninstalled_app_rejects_without_partial_registry_mutation() -> None:
    linker, api, dispatch, events = _linker(apps=())
    dispatch_key = ActionHandlerKey(
        namespace=AppNamespace(app="shop"),
        module="backend",
        action="index",
    )
    module = ApplicationRuntimeModule(
        app_id=AppId("shop"),
        dispatch_handlers=(
            ActionDispatchDefinition(
                dispatch_key,
                DispatchHandlerId("shop-index"),
            ),
        ),
        api_methods=(_api("shop"),),
        event_handlers=(
            _event("shop-saved", owner=ApplicationEventOwner(AppId("shop"))),
        ),
        plugins=(),
    )

    result = await linker.link((module,))

    assert isinstance(result, RuntimeLinkRejected)
    assert RuntimeLinkRejectReason.APP_NOT_INSTALLED in {
        issue.reason for issue in result.issues
    }
    assert type(api.resolve(_api("shop").target)).__name__ == "ApiMethodMissing"
    assert isinstance(dispatch.action_id(dispatch_key), HandlerMissing)
    assert events.matching(
        EventKey(AppId("shop"), EventName("saved"))
    ).definitions == ()


@pytest.mark.asyncio
async def test_duplicate_planned_api_target_rejects_before_any_apply() -> None:
    linker, api, dispatch, events = _linker()
    target_a = _api("shop", "same")
    target_b = _api("shop", "same")
    module = ApplicationRuntimeModule(
        app_id=AppId("shop"),
        dispatch_handlers=(),
        api_methods=(target_a, target_b),
        event_handlers=(),
        plugins=(),
    )

    result = await linker.link((module,))

    assert isinstance(result, RuntimeLinkRejected)
    assert RuntimeLinkRejectReason.API_TARGET_CONFLICT in {
        issue.reason for issue in result.issues
    }
    assert type(api.resolve(target_a.target)).__name__ == "ApiMethodMissing"


@pytest.mark.asyncio
async def test_duplicate_app_module_is_rejected() -> None:
    linker, _, _, _ = _linker()
    first = ApplicationRuntimeModule(
        app_id=AppId("shop"),
        dispatch_handlers=(),
        api_methods=(),
        event_handlers=(),
        plugins=(),
    )
    second = ApplicationRuntimeModule(
        app_id=AppId("shop"),
        dispatch_handlers=(),
        api_methods=(),
        event_handlers=(),
        plugins=(),
    )
    result = await linker.link((first, second))
    assert isinstance(result, RuntimeLinkRejected)
    assert RuntimeLinkRejectReason.DUPLICATE_APP_MODULE in {
        issue.reason for issue in result.issues
    }


@pytest.mark.asyncio
async def test_foreign_dispatch_namespace_and_event_owner_are_rejected() -> None:
    linker, _, dispatch, events = _linker()
    foreign_key = ActionHandlerKey(
        namespace=AppNamespace(app="blog"),
        module="backend",
        action="index",
    )
    module = ApplicationRuntimeModule(
        app_id=AppId("shop"),
        dispatch_handlers=(
            ActionDispatchDefinition(
                foreign_key,
                DispatchHandlerId("bad"),
            ),
        ),
        api_methods=(),
        event_handlers=(
            _event("foreign-owner", owner=ApplicationEventOwner(AppId("blog"))),
        ),
        plugins=(),
    )

    result = await linker.link((module,))

    assert isinstance(result, RuntimeLinkRejected)
    reasons = {issue.reason for issue in result.issues}
    assert RuntimeLinkRejectReason.FOREIGN_DISPATCH_TARGET in reasons
    assert RuntimeLinkRejectReason.FOREIGN_EVENT_OWNER in reasons
    assert isinstance(dispatch.action_id(foreign_key), HandlerMissing)
    assert events.matching(
        EventKey(AppId("shop"), EventName("saved"))
    ).definitions == ()


@pytest.mark.asyncio
async def test_plugin_runtime_requires_installed_enabled_plugin() -> None:
    linker, api, dispatch, events = _linker()
    plugin_key = PluginKey(AppId("shop"), PluginId("reviews"))
    plugin = PluginRuntimeModule(
        key=plugin_key,
        dispatch_handlers=(
            PluginAvailabilityDefinition(plugin_key),
        ),
        api_methods=(),
        event_handlers=(
            _event(
                "reviews-event",
                owner=PluginEventOwner(plugin_key),
            ),
        ),
    )
    module = ApplicationRuntimeModule(
        app_id=AppId("shop"),
        dispatch_handlers=(),
        api_methods=(),
        event_handlers=(),
        plugins=(plugin,),
    )

    result = await linker.link((module,))

    assert isinstance(result, RuntimeLinkRejected)
    assert RuntimeLinkRejectReason.PLUGIN_NOT_INSTALLED in {
        issue.reason for issue in result.issues
    }
    assert type(
        dispatch.plugin_available("shop", "reviews")
    ).__name__ == "PluginMissing"
    assert events.matching(
        EventKey(AppId("shop"), EventName("saved"))
    ).definitions == ()


@pytest.mark.asyncio
async def test_installed_plugin_can_link_plugin_namespace_and_cross_app_event_source() -> None:
    linker, _, dispatch, events = _linker(
        apps=("shop",),
        plugins=(("shop", "reviews"),),
    )
    plugin_key = PluginKey(AppId("shop"), PluginId("reviews"))
    dispatch_key = ActionHandlerKey(
        namespace=PluginNamespace(app="shop", plugin="reviews"),
        module="frontend",
        action="list",
    )
    plugin = PluginRuntimeModule(
        key=plugin_key,
        dispatch_handlers=(
            PluginAvailabilityDefinition(plugin_key),
            ActionDispatchDefinition(
                dispatch_key,
                DispatchHandlerId("reviews-list"),
            ),
        ),
        api_methods=(),
        event_handlers=(
            _event(
                "reviews-cross-app",
                owner=PluginEventOwner(plugin_key),
                source_app="webasyst",
            ),
        ),
    )
    module = ApplicationRuntimeModule(
        app_id=AppId("shop"),
        dispatch_handlers=(),
        api_methods=(),
        event_handlers=(),
        plugins=(plugin,),
    )

    result = await linker.link((module,))

    assert isinstance(result, RuntimeLinkSucceeded)
    assert isinstance(dispatch.plugin_available("shop", "reviews"), PluginAvailable)
    assert dispatch.action_id(dispatch_key) == HandlerRegistered(
        handler_id="reviews-list"
    )
    assert tuple(
        definition.handler_id.value
        for definition in events.matching(
            EventKey(AppId("webasyst"), EventName("saved"))
        ).definitions
    ) == ("reviews-cross-app",)
