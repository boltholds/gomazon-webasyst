from gomazon_webasyst.application.ports.dispatch_registry import DispatchRegistry
from gomazon_webasyst.contracts.dispatch import (
    ActionDispatch,
    ControllerTarget,
    DefaultDispatch,
    DispatchRequest,
    DispatchTarget,
    MultiActionTarget,
    PluginNamespace,
    SingleActionTarget,
)

from .errors import DispatchTargetNotFound, PluginUnavailable
from .keys import action_key, module_key


class DispatchResolver:
    def __init__(self, registry: DispatchRegistry):
        self._registry = registry

    def resolve(
        self, request: DispatchRequest, *, try_default: bool = False
    ) -> DispatchTarget:
        namespace = request.namespace
        if isinstance(namespace, PluginNamespace) and not self._registry.plugin_available(
            namespace.app, namespace.plugin
        ):
            raise PluginUnavailable(
                f"plugin {namespace.app}/{namespace.plugin} is not enabled"
            )

        m_key = module_key(request)
        if isinstance(request, ActionDispatch):
            a_key = action_key(request)
            handler_id = self._registry.controller_id(a_key)
            if handler_id is not None:
                return ControllerTarget(handler_id=handler_id)

            handler_id = self._registry.action_id(a_key)
            if handler_id is not None:
                return SingleActionTarget(handler_id=handler_id)

            handler_id = self._registry.actions_id(m_key)
            if handler_id is not None:
                return MultiActionTarget(
                    handler_id=handler_id,
                    action_method=request.action,
                )

            if try_default:
                return self.resolve(
                    DefaultDispatch(namespace=request.namespace, module=request.module),
                    try_default=False,
                )
        else:
            handler_id = self._registry.controller_id(m_key)
            if handler_id is not None:
                return ControllerTarget(handler_id=handler_id)

            handler_id = self._registry.action_id(m_key)
            if handler_id is not None:
                return SingleActionTarget(handler_id=handler_id)

            handler_id = self._registry.actions_id(m_key)
            if handler_id is not None:
                return MultiActionTarget(
                    handler_id=handler_id,
                    action_method="default",
                )

        raise DispatchTargetNotFound(
            f"no registered handler for {request.namespace!r}/{request.module}"
        )
