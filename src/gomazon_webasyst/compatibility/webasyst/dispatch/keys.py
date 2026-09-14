from gomazon_webasyst.contracts.dispatch import (
    ActionDispatch,
    ActionHandlerKey,
    DispatchRequest,
    ModuleHandlerKey,
)


def module_key(request: DispatchRequest) -> ModuleHandlerKey:
    return ModuleHandlerKey(namespace=request.namespace, module=request.module)


def action_key(request: ActionDispatch) -> ActionHandlerKey:
    return ActionHandlerKey(
        namespace=request.namespace,
        module=request.module,
        action=request.action,
    )
