from gomazon_webasyst.application.app_values import AppId, PluginId, PluginRef
from gomazon_webasyst.application.ports.application_registry import (
    ApplicationEnabled,
    ApplicationRegistry,
    PluginEnabled,
)
from gomazon_webasyst.application.ports.handler_registry import HandlerRegistry
from gomazon_webasyst.contracts.dispatch import (
    ActionDispatch,
    AppNamespace,
    ControllerTarget,
    DefaultDispatch,
    DispatchRequest,
    DispatchTarget,
    HandlerRegistered,
    MultiActionTarget,
    PluginNamespace,
    SingleActionTarget,
)

from .errors import (
    ApplicationUnavailable,
    DispatchTargetNotFound,
    PluginUnavailable,
)
from .keys import action_key, module_key


class DispatchResolver:
    def __init__(
        self,
        handlers: HandlerRegistry,
        applications: ApplicationRegistry,
    ) -> None:
        self._handlers = handlers
        self._applications = applications

    def resolve(
        self,
        request: DispatchRequest,
        *,
        try_default: bool = False,
    ) -> DispatchTarget:
        self._require_namespace_available(request)

        m_key = module_key(request)
        if isinstance(request, ActionDispatch):
            a_key = action_key(request)
            controller = self._handlers.controller_id(a_key)
            if isinstance(controller, HandlerRegistered):
                return ControllerTarget(handler_id=controller.handler_id)

            action = self._handlers.action_id(a_key)
            if isinstance(action, HandlerRegistered):
                return SingleActionTarget(handler_id=action.handler_id)

            actions = self._handlers.actions_id(m_key)
            if isinstance(actions, HandlerRegistered):
                return MultiActionTarget(
                    handler_id=actions.handler_id,
                    action_method=request.action,
                )

            if try_default:
                return self.resolve(
                    DefaultDispatch(
                        namespace=request.namespace,
                        module=request.module,
                    ),
                    try_default=False,
                )
        else:
            controller = self._handlers.controller_id(m_key)
            if isinstance(controller, HandlerRegistered):
                return ControllerTarget(handler_id=controller.handler_id)

            action = self._handlers.action_id(m_key)
            if isinstance(action, HandlerRegistered):
                return SingleActionTarget(handler_id=action.handler_id)

            actions = self._handlers.actions_id(m_key)
            if isinstance(actions, HandlerRegistered):
                return MultiActionTarget(
                    handler_id=actions.handler_id,
                    action_method="default",
                )

        raise DispatchTargetNotFound(
            f"no registered handler for "
            f"{request.namespace!r}/{request.module}"
        )

    def _require_namespace_available(
        self,
        request: DispatchRequest,
    ) -> None:
        namespace = request.namespace
        if isinstance(namespace, PluginNamespace):
            self._require_plugin_available(namespace)
            return
        if isinstance(namespace, AppNamespace):
            self._require_app_available(namespace)
            return
        raise AssertionError("unsupported dispatch namespace")

    def _require_app_available(self, namespace: AppNamespace) -> None:
        try:
            app_id = AppId(namespace.app)
        except ValueError as exc:
            raise ApplicationUnavailable(
                f"application {namespace.app} is not enabled"
            ) from exc

        resolution = self._applications.resolve_app(app_id)
        if not isinstance(resolution, ApplicationEnabled):
            raise ApplicationUnavailable(
                f"application {namespace.app} is not enabled"
            )

    def _require_plugin_available(
        self,
        namespace: PluginNamespace,
    ) -> None:
        try:
            plugin_ref = PluginRef(
                AppId(namespace.app),
                PluginId(namespace.plugin),
            )
        except ValueError as exc:
            raise PluginUnavailable(
                f"plugin {namespace.app}/{namespace.plugin} is not enabled"
            ) from exc

        resolution = self._applications.resolve_plugin(plugin_ref)
        if not isinstance(resolution, PluginEnabled):
            raise PluginUnavailable(
                f"plugin {namespace.app}/{namespace.plugin} is not enabled"
            )
