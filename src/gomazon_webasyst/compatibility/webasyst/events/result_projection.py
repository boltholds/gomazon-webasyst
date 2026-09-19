from dataclasses import dataclass
from typing import TypeAlias

from pydantic import JsonValue

from gomazon_webasyst.application.events.composites.contracts import (
    EventDispatchReport,
    EventDispatchResult,
)
from gomazon_webasyst.application.events.vo.owners import (
    ApplicationEventOwner,
    PluginEventOwner,
)
from gomazon_webasyst.application.events.vo.payload import LegacyEventPayload


@dataclass(slots=True, frozen=True)
class LegacyEventArrayKeysDisabled:
    pass


@dataclass(slots=True, frozen=True)
class LegacyEventArrayKeys:
    keys: tuple[str, ...]


LegacyEventArrayKeysMode: TypeAlias = (
    LegacyEventArrayKeysDisabled | LegacyEventArrayKeys
)


class LegacyEventResultProjectionError(ValueError):
    pass


class LegacyEventResultProjector:
    def project(
        self,
        report: EventDispatchReport,
        *,
        array_keys: LegacyEventArrayKeysMode,
    ) -> dict[str, JsonValue]:
        result: dict[str, JsonValue] = {}
        for item in report.results:
            key = self._result_key(report, item)
            value = self._payload_value(item)
            if isinstance(item.owner, PluginEventOwner):
                value = self._apply_plugin_array_keys(value, array_keys)
            result[key] = value
        return result

    @staticmethod
    def _result_key(
        report: EventDispatchReport,
        item: EventDispatchResult,
    ) -> str:
        owner = item.owner
        if isinstance(owner, ApplicationEventOwner):
            return owner.app_id.value
        if isinstance(owner, PluginEventOwner):
            plugin_key = owner.key
            if report.event.app_id == plugin_key.app_id:
                return f"{plugin_key.plugin_id.value}-plugin"
            return (
                f"{plugin_key.app_id.value}_"
                f"{plugin_key.plugin_id.value}-plugin"
            )
        raise AssertionError("unsupported event result owner")

    @staticmethod
    def _payload_value(item: EventDispatchResult) -> JsonValue:
        if isinstance(item.value, LegacyEventPayload):
            return item.value.value
        return item.value.model_dump(mode="json")

    @staticmethod
    def _apply_plugin_array_keys(
        value: JsonValue,
        mode: LegacyEventArrayKeysMode,
    ) -> JsonValue:
        if isinstance(mode, LegacyEventArrayKeysDisabled):
            return value

        if isinstance(value, dict):
            normalized: dict[str, JsonValue] = dict(value)
        else:
            normalized = {"": value}

        for key in mode.keys:
            if key not in normalized or normalized[key] is None:
                normalized[key] = ""
        return normalized
