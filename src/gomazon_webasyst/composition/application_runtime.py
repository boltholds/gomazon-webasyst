from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from gomazon_webasyst.application.api_execution.entities.method_definition import (
    ApiMethodDefinition,
)
from gomazon_webasyst.application.events.composites.dispatcher import EventDispatcher
from gomazon_webasyst.application.events.services.pattern_matcher import EventPatternMatcher
from gomazon_webasyst.application.ports.api_method_registry import ApiMethodRegistry
from gomazon_webasyst.application.ports.dispatch_registration import (
    DispatchRegistrationSink,
)
from gomazon_webasyst.application.ports.dispatch_registry import DispatchRegistry
from gomazon_webasyst.application.ports.event_handlers import EventHandlerRegistry
from gomazon_webasyst.application.ports.installed_application_catalog import (
    InstalledApplicationCatalog,
)
from gomazon_webasyst.application.ports.installed_plugin_catalog import (
    InstalledPluginCatalog,
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
from gomazon_webasyst.compatibility.webasyst.dispatch.registry import (
    InMemoryDispatchRegistry,
)
from gomazon_webasyst.compatibility.webasyst.events.pattern_matcher import (
    RejectUnsupportedLegacyRegexMatcher,
)
from gomazon_webasyst.infrastructure.api_execution.method_registry import (
    InMemoryApiMethodRegistry,
)
from gomazon_webasyst.infrastructure.events.registry import (
    InMemoryEventHandlerRegistry,
)
from gomazon_webasyst.infrastructure.plugins.filesystem_catalog import (
    FilesystemInstalledPluginCatalog,
)


@dataclass(slots=True, frozen=True)
class FilesystemPluginCatalogSource:
    root: Path


@dataclass(slots=True, frozen=True)
class ProvidedPluginCatalogSource:
    catalog: InstalledPluginCatalog


PluginCatalogSource: TypeAlias = (
    FilesystemPluginCatalogSource | ProvidedPluginCatalogSource
)


@dataclass(slots=True, frozen=True)
class ApplicationRuntimePending:
    pass


@dataclass(slots=True, frozen=True)
class ApplicationRuntimeReady:
    installed_plugins: InstalledPluginCatalog
    linked: RuntimeLinkSucceeded


ApplicationRuntimeState: TypeAlias = ApplicationRuntimePending | ApplicationRuntimeReady


class ApplicationRuntimeInitializationError(RuntimeError):
    def __init__(self, rejected: RuntimeLinkRejected) -> None:
        self.rejected = rejected
        details = ", ".join(
            f"{issue.reason.value}:{issue.subject}"
            for issue in rejected.issues
        )
        super().__init__(f"application runtime linking rejected: {details}")


class ApplicationRuntimeBootstrap:
    def __init__(
        self,
        *,
        installed_applications: InstalledApplicationCatalog,
        plugin_source: PluginCatalogSource,
        modules: tuple[ApplicationRuntimeModule, ...],
        api_methods: ApiMethodRegistry,
        dispatch: DispatchRegistrationSink,
        events: EventHandlerRegistry,
    ) -> None:
        self._installed_applications = installed_applications
        self._plugin_source = plugin_source
        self._modules = modules
        self._api_methods = api_methods
        self._dispatch = dispatch
        self._events = events
        self._state: ApplicationRuntimeState = ApplicationRuntimePending()

    @property
    def state(self) -> ApplicationRuntimeState:
        return self._state

    async def initialize(self) -> ApplicationRuntimeReady:
        if isinstance(self._state, ApplicationRuntimeReady):
            return self._state

        installed_plugins = await self._installed_plugins()
        linker = ApplicationRuntimeLinker(
            installed_applications=self._installed_applications,
            installed_plugins=installed_plugins,
            api_methods=self._api_methods,
            dispatch=self._dispatch,
            events=self._events,
        )
        result = await linker.link(self._modules)
        if isinstance(result, RuntimeLinkRejected):
            raise ApplicationRuntimeInitializationError(result)

        ready = ApplicationRuntimeReady(
            installed_plugins=installed_plugins,
            linked=result,
        )
        self._state = ready
        return ready

    async def _installed_plugins(self) -> InstalledPluginCatalog:
        if isinstance(self._plugin_source, ProvidedPluginCatalogSource):
            return self._plugin_source.catalog
        if isinstance(self._plugin_source, FilesystemPluginCatalogSource):
            snapshot = await self._installed_applications.snapshot()
            return FilesystemInstalledPluginCatalog(
                self._plugin_source.root,
                snapshot,
            )
        raise AssertionError("unsupported plugin catalog source")


@dataclass(slots=True, frozen=True)
class ApplicationRuntimeComponents:
    api_method_registry: ApiMethodRegistry
    dispatch_registry: DispatchRegistry
    dispatch_registration: DispatchRegistrationSink
    event_registry: EventHandlerRegistry
    event_dispatcher: EventDispatcher
    bootstrap: ApplicationRuntimeBootstrap


def create_application_runtime_components(
    *,
    installed_applications: InstalledApplicationCatalog,
    plugin_source: PluginCatalogSource,
    modules: tuple[ApplicationRuntimeModule, ...],
) -> ApplicationRuntimeComponents:
    api_methods = InMemoryApiMethodRegistry()
    dispatch = InMemoryDispatchRegistry()
    events = InMemoryEventHandlerRegistry(
        EventPatternMatcher(RejectUnsupportedLegacyRegexMatcher())
    )
    bootstrap = ApplicationRuntimeBootstrap(
        installed_applications=installed_applications,
        plugin_source=plugin_source,
        modules=modules,
        api_methods=api_methods,
        dispatch=dispatch,
        events=events,
    )
    return ApplicationRuntimeComponents(
        api_method_registry=api_methods,
        dispatch_registry=dispatch,
        dispatch_registration=dispatch,
        event_registry=events,
        event_dispatcher=EventDispatcher(events),
        bootstrap=bootstrap,
    )


def create_default_application_runtime_modules() -> tuple[
    ApplicationRuntimeModule,
    ...,
]:
    return ()
