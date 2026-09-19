from dataclasses import dataclass
from typing import Protocol, TypeAlias

from gomazon_webasyst.application.events.vo.identity import EventName
from gomazon_webasyst.application.events.vo.patterns import (
    ExactEventPattern,
    LegacyRegexEventPattern,
    PrefixEventPattern,
    EventNamePattern,
)


@dataclass(slots=True, frozen=True)
class EventPatternMatched:
    pass


@dataclass(slots=True, frozen=True)
class EventPatternNotMatched:
    pass


EventPatternMatch: TypeAlias = EventPatternMatched | EventPatternNotMatched


class LegacyRegexEventMatcher(Protocol):
    def match(
        self,
        expression: str,
        event_name: EventName,
    ) -> EventPatternMatch: ...


class EventPatternMatcher:
    def __init__(self, legacy_regex: LegacyRegexEventMatcher) -> None:
        self._legacy_regex = legacy_regex

    def match(
        self,
        pattern: EventNamePattern,
        event_name: EventName,
    ) -> EventPatternMatch:
        if isinstance(pattern, ExactEventPattern):
            if pattern.name == event_name:
                return EventPatternMatched()
            return EventPatternNotMatched()
        if isinstance(pattern, PrefixEventPattern):
            if event_name.value.startswith(pattern.prefix.value):
                return EventPatternMatched()
            return EventPatternNotMatched()
        if isinstance(pattern, LegacyRegexEventPattern):
            return self._legacy_regex.match(pattern.expression, event_name)
        raise AssertionError("unsupported event pattern")
