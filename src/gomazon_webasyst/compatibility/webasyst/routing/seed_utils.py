from collections.abc import Mapping

from gomazon_webasyst.contracts.dispatch import (
    ActionDispatch,
    AppNamespace,
    DefaultDispatch,
    DispatchRequest,
    PluginNamespace,
)
from gomazon_webasyst.contracts.routing import (
    ActionOnlySeed,
    ActionSeed,
    AnyAppRouteConstraint,
    AppRouteConstraint,
    DispatchSeed,
    EmptySeed,
    ModuleRouteConstraint,
    ModuleSeed,
    PluginActionOnlySeed,
    PluginActionSeed,
    PluginModuleSeed,
    PluginSeed,
)


CONTROL_NAMES = frozenset({"module", "action", "plugin"})


def seed_to_controls(seed: DispatchSeed) -> dict[str, str]:
    match seed:
        case EmptySeed():
            return {}
        case ModuleSeed(module=module):
            return {"module": module}
        case ActionOnlySeed(action=action):
            return {"action": action}
        case ActionSeed(module=module, action=action):
            return {"module": module, "action": action}
        case PluginSeed(plugin=plugin):
            return {"plugin": plugin}
        case PluginActionOnlySeed(plugin=plugin, action=action):
            return {"plugin": plugin, "action": action}
        case PluginModuleSeed(plugin=plugin, module=module):
            return {"plugin": plugin, "module": module}
        case PluginActionSeed(plugin=plugin, module=module, action=action):
            return {"plugin": plugin, "module": module, "action": action}
    raise TypeError(f"unsupported dispatch seed: {type(seed)!r}")


def seed_from_controls(values: Mapping[str, str]) -> DispatchSeed:
    has_module = "module" in values
    has_action = "action" in values
    has_plugin = "plugin" in values

    if not has_plugin:
        if not has_module and not has_action:
            return EmptySeed()
        if not has_module:
            return ActionOnlySeed(action=values["action"])
        if not has_action:
            return ModuleSeed(module=values["module"])
        return ActionSeed(module=values["module"], action=values["action"])

    plugin = values["plugin"]
    if not has_module and not has_action:
        return PluginSeed(plugin=plugin)
    if not has_module:
        return PluginActionOnlySeed(plugin=plugin, action=values["action"])
    if not has_action:
        return PluginModuleSeed(plugin=plugin, module=values["module"])
    return PluginActionSeed(
        plugin=plugin,
        module=values["module"],
        action=values["action"],
    )


def merge_seed(
    base: DispatchSeed,
    captures: Mapping[str, str],
    explicit: DispatchSeed,
) -> DispatchSeed:
    values = seed_to_controls(base)
    for key in CONTROL_NAMES:
        if key in captures and key not in values:
            values[key] = captures[key]
    values.update(seed_to_controls(explicit))
    return seed_from_controls(values)


def app_route_constraint(seed: DispatchSeed) -> AppRouteConstraint:
    match seed:
        case ModuleSeed(module=module) | ActionSeed(module=module) | PluginModuleSeed(module=module) | PluginActionSeed(module=module):
            return ModuleRouteConstraint(module=module)
        case EmptySeed() | ActionOnlySeed() | PluginSeed() | PluginActionOnlySeed():
            return AnyAppRouteConstraint()
    raise TypeError(f"unsupported dispatch seed: {type(seed)!r}")


def dispatch_from_seed(app: str, seed: DispatchSeed, *, default_module: str) -> DispatchRequest:
    match seed:
        case EmptySeed():
            return DefaultDispatch(namespace=AppNamespace(app=app), module=default_module)
        case ModuleSeed(module=module):
            return DefaultDispatch(namespace=AppNamespace(app=app), module=module)
        case ActionOnlySeed(action=action):
            return ActionDispatch(
                namespace=AppNamespace(app=app),
                module=default_module,
                action=action,
            )
        case ActionSeed(module=module, action=action):
            return ActionDispatch(
                namespace=AppNamespace(app=app),
                module=module,
                action=action,
            )
        case PluginSeed(plugin=plugin):
            return DefaultDispatch(
                namespace=PluginNamespace(app=app, plugin=plugin),
                module=default_module,
            )
        case PluginActionOnlySeed(plugin=plugin, action=action):
            return ActionDispatch(
                namespace=PluginNamespace(app=app, plugin=plugin),
                module=default_module,
                action=action,
            )
        case PluginModuleSeed(plugin=plugin, module=module):
            return DefaultDispatch(
                namespace=PluginNamespace(app=app, plugin=plugin),
                module=module,
            )
        case PluginActionSeed(plugin=plugin, module=module, action=action):
            return ActionDispatch(
                namespace=PluginNamespace(app=app, plugin=plugin),
                module=module,
                action=action,
            )
    raise TypeError(f"unsupported dispatch seed: {type(seed)!r}")
