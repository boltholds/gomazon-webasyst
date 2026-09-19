from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.events.vo.identity import EventName


@dataclass(slots=True, frozen=True)
class ExactEventSource:
    app_id: AppId


@dataclass(slots=True, frozen=True)
class AnyEventSource:
    pass


EventSourceSelector: TypeAlias = ExactEventSource | AnyEventSource


@dataclass(slots=True, frozen=True)
class ExactEventPattern:
    name: EventName


@dataclass(slots=True, frozen=True)
class EventNamePrefix:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("event name prefix must not be empty")


@dataclass(slots=True, frozen=True)
class PrefixEventPattern:
    prefix: EventNamePrefix


@dataclass(slots=True, frozen=True)
class LegacyRegexEventPattern:
    expression: str

    def __post_init__(self) -> None:
        if not self.expression:
            raise ValueError("legacy event regex must not be empty")


EventNamePattern: TypeAlias = (
    ExactEventPattern | PrefixEventPattern | LegacyRegexEventPattern
)
