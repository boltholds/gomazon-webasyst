from gomazon_webasyst.application.api_execution.vo.method import ApiMethodTarget
from gomazon_webasyst.application.events.vo.owners import (
    ApplicationEventOwner,
    PluginEventOwner,
)
from gomazon_webasyst.application.ports.api_method_registry import (
    ApiMethodMissing,
    ApiMethodRegistrationRejected,
    ApiMethodRegistry,
)
from gomazon_webasyst.application.ports.dispatch_registration import (
    DispatchRegistrationAvailable,
    DispatchRegistrationRejected,
    DispatchRegistrationSink,
)
from gomazon_webasyst.application.ports.event_handlers import (
    EventHandlerRegistrationAvailable,
    EventHandlerRegistrationRejected,
    EventHandlerRegistry,
)
from gomazon_webasyst.application.ports.installed_application_catalog import (
    InstalledApplicationCatalog,
    InstalledApplicationMissing,
)
from gomazon_webasyst.application.ports.installed_plugin_catalog import (
    InstalledPluginCatalog,
    InstalledPluginMissing,
)
from gomazon_webasyst.application.runtime.composites.results import (
    RuntimeLinkIssue,
    RuntimeLinkRejected,
    RuntimeLinkResult,
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
    ControllerDispatchDefinition,
    DispatchRuntimeDefinition,
    MultiActionDispatchDefinition,
    PluginAvailabilityDefinition,
)
from gomazon_webasyst.contracts.dispatch import AppNamespace, PluginNamespace
from gomazon_webasyst.contracts.enums import RuntimeLinkRejectReason


class ApplicationRuntimeLinker:
    def __init__(
        self,
        *,
        installed_applications: InstalledApplicationCatalog,
        installed_plugins: InstalledPluginCatalog,
        api_methods: ApiMethodRegistry,
        dispatch: DispatchRegistrationSink,
        events: EventHandlerRegistry,
    ) -> None:
        self._installed_applications = installed_applications
        self._installed_plugins = installed_plugins
        self._api_methods = api_methods
        self._dispatch = dispatch
        self._events = events

    async def link(
        self,
        modules: tuple[ApplicationRuntimeModule, ...],
    ) -> RuntimeLinkResult:
        issues = await self._validate(modules)
        if issues:
            return RuntimeLinkRejected(tuple(issues))

        for module in modules:
            self._apply_module(module)
            for plugin in module.plugins:
                self._apply_plugin(plugin)

        return RuntimeLinkSucceeded(
            applications=tuple(module.app_id for module in modules),
            plugins=tuple(
                plugin.key
                for module in modules
                for plugin in module.plugins
            ),
        )

    async def _validate(
        self,
        modules: tuple[ApplicationRuntimeModule, ...],
    ) -> list[RuntimeLinkIssue]:
        issues: list[RuntimeLinkIssue] = []
        seen_apps = set()
        planned_api: set[ApiMethodTarget] = set()
        planned_dispatch: set[tuple[str, object]] = set()
        planned_events = set()

        for module in modules:
            if module.app_id in seen_apps:
                issues.append(
                    RuntimeLinkIssue(
                        RuntimeLinkRejectReason.DUPLICATE_APP_MODULE,
                        module.app_id.value,
                    )
                )
                continue
            seen_apps.add(module.app_id)

            app_resolution = await self._installed_applications.resolve(
                module.app_id
            )
            if isinstance(app_resolution, InstalledApplicationMissing):
                issues.append(
                    RuntimeLinkIssue(
                        RuntimeLinkRejectReason.APP_NOT_INSTALLED,
                        module.app_id.value,
                    )
                )

            self._validate_api_definitions(
                module.api_methods,
                planned_api,
                issues,
            )
            self._validate_dispatch_definitions(
                module.dispatch_handlers,
                module.app_id.value,
                "",
                planned_dispatch,
                issues,
            )
            self._validate_app_event_owners(
                module,
                planned_events,
                issues,
            )

            for plugin in module.plugins:
                plugin_resolution = await self._installed_plugins.resolve(
                    plugin.key
                )
                if isinstance(plugin_resolution, InstalledPluginMissing):
                    issues.append(
                        RuntimeLinkIssue(
                            RuntimeLinkRejectReason.PLUGIN_NOT_INSTALLED,
                            (
                                f"{plugin.key.app_id.value}."
                                f"{plugin.key.plugin_id.value}"
                            ),
                        )
                    )

                self._validate_api_definitions(
                    plugin.api_methods,
                    planned_api,
                    issues,
                )
                self._validate_dispatch_definitions(
                    plugin.dispatch_handlers,
                    plugin.key.app_id.value,
                    plugin.key.plugin_id.value,
                    planned_dispatch,
                    issues,
                )
                self._validate_plugin_event_owners(
                    plugin,
                    planned_events,
                    issues,
                )

        return issues

    def _validate_api_definitions(
        self,
        definitions,
        planned: set[ApiMethodTarget],
        issues: list[RuntimeLinkIssue],
    ) -> None:
        for definition in definitions:
            target = definition.target
            if target in planned or not isinstance(
                self._api_methods.resolve(target),
                ApiMethodMissing,
            ):
                issues.append(
                    RuntimeLinkIssue(
                        RuntimeLinkRejectReason.API_TARGET_CONFLICT,
                        (
                            f"{target.app_id.value}."
                            f"{target.method.value}"
                        ),
                    )
                )
            planned.add(target)

    def _validate_dispatch_definitions(
        self,
        definitions: tuple[DispatchRuntimeDefinition, ...],
        app_id: str,
        plugin_id: str,
        planned: set[tuple[str, object]],
        issues: list[RuntimeLinkIssue],
    ) -> None:
        for definition in definitions:
            if not self._dispatch_owned_by(
                definition,
                app_id=app_id,
                plugin_id=plugin_id,
            ):
                issues.append(
                    RuntimeLinkIssue(
                        RuntimeLinkRejectReason.FOREIGN_DISPATCH_TARGET,
                        self._dispatch_subject(definition),
                    )
                )

            collision_key = self._dispatch_collision_key(definition)
            if collision_key in planned or not isinstance(
                self._dispatch.check(definition),
                DispatchRegistrationAvailable,
            ):
                issues.append(
                    RuntimeLinkIssue(
                        RuntimeLinkRejectReason.DISPATCH_TARGET_CONFLICT,
                        self._dispatch_subject(definition),
                    )
                )
            planned.add(collision_key)

    def _validate_app_event_owners(
        self,
        module: ApplicationRuntimeModule,
        planned: set,
        issues: list[RuntimeLinkIssue],
    ) -> None:
        for definition in module.event_handlers:
            if definition.owner != ApplicationEventOwner(module.app_id):
                issues.append(
                    RuntimeLinkIssue(
                        RuntimeLinkRejectReason.FOREIGN_EVENT_OWNER,
                        definition.handler_id.value,
                    )
                )
            self._validate_event_registration(
                definition.handler_id,
                planned,
                issues,
            )

    def _validate_plugin_event_owners(
        self,
        module: PluginRuntimeModule,
        planned: set,
        issues: list[RuntimeLinkIssue],
    ) -> None:
        for definition in module.event_handlers:
            if definition.owner != PluginEventOwner(module.key):
                issues.append(
                    RuntimeLinkIssue(
                        RuntimeLinkRejectReason.FOREIGN_EVENT_OWNER,
                        definition.handler_id.value,
                    )
                )
            self._validate_event_registration(
                definition.handler_id,
                planned,
                issues,
            )

    def _validate_event_registration(
        self,
        handler_id,
        planned: set,
        issues: list[RuntimeLinkIssue],
    ) -> None:
        if handler_id in planned or not isinstance(
            self._events.check(handler_id),
            EventHandlerRegistrationAvailable,
        ):
            issues.append(
                RuntimeLinkIssue(
                    RuntimeLinkRejectReason.EVENT_HANDLER_CONFLICT,
                    handler_id.value,
                )
            )
        planned.add(handler_id)

    def _apply_module(self, module: ApplicationRuntimeModule) -> None:
        for definition in module.api_methods:
            result = self._api_methods.register(definition)
            if isinstance(result, ApiMethodRegistrationRejected):
                raise AssertionError("validated API method registration rejected")
        for definition in module.dispatch_handlers:
            result = self._dispatch.register(definition)
            if isinstance(result, DispatchRegistrationRejected):
                raise AssertionError("validated dispatch registration rejected")
        for definition in module.event_handlers:
            result = self._events.register(definition)
            if isinstance(result, EventHandlerRegistrationRejected):
                raise AssertionError("validated event registration rejected")

    def _apply_plugin(self, module: PluginRuntimeModule) -> None:
        for definition in module.api_methods:
            result = self._api_methods.register(definition)
            if isinstance(result, ApiMethodRegistrationRejected):
                raise AssertionError("validated plugin API registration rejected")
        for definition in module.dispatch_handlers:
            result = self._dispatch.register(definition)
            if isinstance(result, DispatchRegistrationRejected):
                raise AssertionError("validated plugin dispatch registration rejected")
        for definition in module.event_handlers:
            result = self._events.register(definition)
            if isinstance(result, EventHandlerRegistrationRejected):
                raise AssertionError("validated plugin event registration rejected")

    @staticmethod
    def _dispatch_owned_by(
        definition: DispatchRuntimeDefinition,
        *,
        app_id: str,
        plugin_id: str,
    ) -> bool:
        if isinstance(definition, PluginAvailabilityDefinition):
            return (
                bool(plugin_id)
                and definition.key.app_id.value == app_id
                and definition.key.plugin_id.value == plugin_id
            )

        namespace = definition.key.namespace
        if plugin_id:
            return (
                isinstance(namespace, PluginNamespace)
                and namespace.app == app_id
                and namespace.plugin == plugin_id
            )
        return isinstance(namespace, AppNamespace) and namespace.app == app_id

    @staticmethod
    def _dispatch_collision_key(
        definition: DispatchRuntimeDefinition,
    ) -> tuple[str, object]:
        if isinstance(definition, ControllerDispatchDefinition):
            return ("controller", definition.key)
        if isinstance(definition, ActionDispatchDefinition):
            return ("action", definition.key)
        if isinstance(definition, MultiActionDispatchDefinition):
            return ("multi_action", definition.key)
        if isinstance(definition, PluginAvailabilityDefinition):
            return ("plugin", definition.key)
        raise AssertionError("unsupported dispatch definition")

    @staticmethod
    def _dispatch_subject(
        definition: DispatchRuntimeDefinition,
    ) -> str:
        if isinstance(definition, PluginAvailabilityDefinition):
            return (
                f"{definition.key.app_id.value}."
                f"{definition.key.plugin_id.value}"
            )
        namespace = definition.key.namespace
        if isinstance(namespace, AppNamespace):
            owner = namespace.app
        else:
            owner = f"{namespace.app}.{namespace.plugin}"
        module = definition.key.module
        action = getattr(definition.key, "action", "")
        suffix = f".{action}" if action else ""
        return f"{owner}:{module}{suffix}"
