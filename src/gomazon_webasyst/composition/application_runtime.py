from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.events.composites.dispatcher import EventDispatcher
from gomazon_webasyst.application.events.services.pattern_matcher import EventPatternMatcher
from gomazon_webasyst.application.ports.api_method_registry import ApiMethodRegistry
from gomazon_webasyst.application.ports.dispatch_registration import (
    DispatchRegistrationSink,
)
from gomazon_webasyst.application.ports.dispatch_registry import DispatchRegistry
from gomazon_webasyst.application.ports.event_handlers import EventHandlerRegistry
from gomazon_webasyst.application.ports.event_publisher import EventPublisher
from gomazon_webasyst.application.ports.installed_application_catalog import (
    InstalledApplicationCatalog,
    InstalledApplicationSnapshot,
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
class ProvidedRuntimeModules:
    modules: tuple[ApplicationRuntimeModule, ...]


class RuntimeModuleFactory(Protocol):
    def __call__(
        self,
        event_publisher: EventPublisher,
    ) -> ApplicationRuntimeModule: ...


@dataclass(slots=True, frozen=True)
class KnownRuntimeModuleFactory:
    app_id: AppId
    build: RuntimeModuleFactory


@dataclass(slots=True, frozen=True)
class InstalledKnownRuntimeModuleFactories:
    factories: tuple[KnownRuntimeModuleFactory, ...]


RuntimeModuleSource: TypeAlias = (
    ProvidedRuntimeModules | InstalledKnownRuntimeModuleFactories
)


@dataclass(slots=True, frozen=True)
class DefaultRuntimeModulePlan:
    pass


@dataclass(slots=True, frozen=True)
class ExplicitRuntimeModulePlan:
    modules: tuple[ApplicationRuntimeModule, ...]


RuntimeModulePlan: TypeAlias = DefaultRuntimeModulePlan | ExplicitRuntimeModulePlan


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


class RuntimeModuleFactoryMismatch(RuntimeError):
    pass


class ApplicationRuntimeBootstrap:
    def __init__(
        self,
        *,
        installed_applications: InstalledApplicationCatalog,
        plugin_source: PluginCatalogSource,
        module_source: RuntimeModuleSource,
        event_publisher: EventPublisher,
        api_methods: ApiMethodRegistry,
        dispatch: DispatchRegistrationSink,
        events: EventHandlerRegistry,
    ) -> None:
        self._installed_applications = installed_applications
        self._plugin_source = plugin_source
        self._module_source = module_source
        self._event_publisher = event_publisher
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

        application_snapshot = await self._installed_applications.snapshot()
        installed_plugins = await self._installed_plugins(application_snapshot)
        modules = self._runtime_modules(application_snapshot)

        linker = ApplicationRuntimeLinker(
            installed_applications=self._installed_applications,
            installed_plugins=installed_plugins,
            api_methods=self._api_methods,
            dispatch=self._dispatch,
            events=self._events,
        )
        result = await linker.link(modules)
        if isinstance(result, RuntimeLinkRejected):
            raise ApplicationRuntimeInitializationError(result)

        ready = ApplicationRuntimeReady(
            installed_plugins=installed_plugins,
            linked=result,
        )
        self._state = ready
        return ready

    async def _installed_plugins(
        self,
        application_snapshot: InstalledApplicationSnapshot,
    ) -> InstalledPluginCatalog:
        if isinstance(self._plugin_source, ProvidedPluginCatalogSource):
            return self._plugin_source.catalog
        if isinstance(self._plugin_source, FilesystemPluginCatalogSource):
            return FilesystemInstalledPluginCatalog(
                self._plugin_source.root,
                application_snapshot,
            )
        raise AssertionError("unsupported plugin catalog source")

    def _runtime_modules(
        self,
        application_snapshot: InstalledApplicationSnapshot,
    ) -> tuple[ApplicationRuntimeModule, ...]:
        if isinstance(self._module_source, ProvidedRuntimeModules):
            return self._module_source.modules

        if isinstance(
            self._module_source,
            InstalledKnownRuntimeModuleFactories,
        ):
            modules: list[ApplicationRuntimeModule] = []
            for application in application_snapshot.applications:
                for known in self._module_source.factories:
                    if known.app_id != application.app_id:
                        continue
                    module = known.build(self._event_publisher)
                    if module.app_id != known.app_id:
                        raise RuntimeModuleFactoryMismatch(
                            "runtime module factory identity mismatch: "
                            f"declared={known.app_id.value}, "
                            f"built={module.app_id.value}"
                        )
                    modules.append(module)
            return tuple(modules)

        raise AssertionError("unsupported runtime module source")


@dataclass(slots=True, frozen=True)
class ApplicationRuntimeComponents:
    api_method_registry: ApiMethodRegistry
    dispatch_registry: DispatchRegistry
    dispatch_registration: DispatchRegistrationSink
    event_registry: EventHandlerRegistry
    event_publisher: EventPublisher
    event_dispatcher: EventDispatcher
    bootstrap: ApplicationRuntimeBootstrap


def create_application_runtime_components(
    *,
    installed_applications: InstalledApplicationCatalog,
    plugin_source: PluginCatalogSource,
    module_source: RuntimeModuleSource,
) -> ApplicationRuntimeComponents:
    api_methods = InMemoryApiMethodRegistry()
    dispatch = InMemoryDispatchRegistry()
    events = InMemoryEventHandlerRegistry(
        EventPatternMatcher(RejectUnsupportedLegacyRegexMatcher())
    )
    event_dispatcher = EventDispatcher(events)
    bootstrap = ApplicationRuntimeBootstrap(
        installed_applications=installed_applications,
        plugin_source=plugin_source,
        module_source=module_source,
        event_publisher=event_dispatcher,
        api_methods=api_methods,
        dispatch=dispatch,
        events=events,
    )
    return ApplicationRuntimeComponents(
        api_method_registry=api_methods,
        dispatch_registry=dispatch,
        dispatch_registration=dispatch,
        event_registry=events,
        event_publisher=event_dispatcher,
        event_dispatcher=event_dispatcher,
        bootstrap=bootstrap,
    )


def create_default_application_runtime_module_factories(
    session_factory,
    *,
    installed_applications: InstalledApplicationCatalog,
    public_root_url: str = "http://localhost/",
    server_timezone=timezone.utc,
) -> tuple[KnownRuntimeModuleFactory, ...]:
    from gomazon_webasyst.composition.contacts import (
        create_contacts_runtime_module,
    )
    from gomazon_webasyst.composition.team import create_team_runtime_module

    return (
        KnownRuntimeModuleFactory(
            app_id=AppId("contacts"),
            build=lambda _event_publisher: create_contacts_runtime_module(
                session_factory
            ),
        ),
        KnownRuntimeModuleFactory(
            app_id=AppId("team"),
            build=lambda event_publisher: create_team_runtime_module(
                session_factory,
                event_publisher=event_publisher,
                installed_applications=installed_applications,
                public_root_url=public_root_url,
                server_timezone=server_timezone,
            ),
        ),
    )
