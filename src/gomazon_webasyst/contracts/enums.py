from enum import StrEnum


class EnumStr(StrEnum):
    """String enum base used by serialized contract discriminators."""


class DispatchSeedKind(EnumStr):
    EMPTY = "empty"
    MODULE = "module"
    ACTION_ONLY = "action_only"
    ACTION = "action"
    PLUGIN = "plugin"
    PLUGIN_ACTION_ONLY = "plugin_action_only"
    PLUGIN_MODULE = "plugin_module"
    PLUGIN_ACTION = "plugin_action"


class AppRouteConstraintKind(EnumStr):
    ANY = "any"
    MODULE = "module"


class SettlementKind(EnumStr):
    APP = "app"
    REDIRECT = "redirect"


class DispatchNamespaceKind(EnumStr):
    APP = "app"
    PLUGIN = "plugin"


class DispatchRequestKind(EnumStr):
    DEFAULT = "default"
    ACTION = "action"


class DispatchTargetKind(EnumStr):
    CONTROLLER = "controller"
    SINGLE_ACTION = "single_action"
    MULTI_ACTION = "multi_action"


class LegacyDispatchOutcomeKind(EnumStr):
    HANDLER = "handler"
