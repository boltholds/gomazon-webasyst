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
    DispatchSeed,
    EmptySeed,
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
    module = values.get("module")
    action = values.get("action")
    plugin = values.get("plugin")

    if plugin is None:
        if module is None and action is None:
            return EmptySeed()
        if module is None:
            return ActionOnlySeed(action=action)
        if action is None:
            return ModuleSeed(module=module)
        return ActionSeed(module=module, action=action)

    if module is None and action is None:
        return PluginSeed(plugin=plugin)
    if module is None:
        return PluginActionOnlySeed(plugin=plugin, action=action)
    if action is None:
        return PluginModuleSeed(plugin=plugin, module=module)
    return PluginActionSeed(plugin=plugin, module=module, action=action)


def merge_seed(
    base: DispatchSeed,
    captures: Mapping[str, str],
    explicit: DispatchSeed,
) -> DispatchSeed:
    values = seed_to_controls(base)
    for key in CONTROL_NAMES:
        value = captures.get(key)
        if value is not None and key not in values:
            values[key] = value
    values.update(seed_to_controls(explicit))
    return seed_from_controls(values)


def explicit_module(seed: DispatchSeed) -> str | None:
    values = seed_to_controls(seed)
    return values.get("module")


def dispatch_from_seed(app: str, seed: DispatchSeed, *, default_module: str) -> DispatchRequest:
    values = seed_to_controls(seed)
    module = values.get("module", default_module)
    action = values.get("action")
    plugin = values.get("plugin")
    namespace = (
        PluginNamespace(app=app, plugin=plugin)
        if plugin is not None
        else AppNamespace(app=app)
    )
    if action is None:
        return DefaultDispatch(namespace=namespace, module=module)
    return ActionDispatch(namespace=namespace, module=module, action=action)
