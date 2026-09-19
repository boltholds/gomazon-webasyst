from gomazon_webasyst.application.events.entities.handler_definition import (
    EventHandlerDefinition,
)
from gomazon_webasyst.application.events.services.pattern_matcher import (
    EventPatternMatched,
    EventPatternMatcher,
)
from gomazon_webasyst.application.events.vo.identity import EventHandlerId, EventKey
from gomazon_webasyst.application.events.vo.patterns import (
    AnyEventSource,
    ExactEventPattern,
    ExactEventSource,
)
from gomazon_webasyst.application.ports.event_handlers import (
    EventHandlerMatchSet,
    EventHandlerRegistered,
    EventHandlerRegistrationAvailable,
    EventHandlerRegistrationCheck,
    EventHandlerRegistrationConflict,
    EventHandlerRegistrationRejected,
    EventHandlerRegistrationResult,
)


class InMemoryEventHandlerRegistry:
    def __init__(self, matcher: EventPatternMatcher) -> None:
        self._matcher = matcher
        self._definitions: list[EventHandlerDefinition] = []
        self._ids: set[EventHandlerId] = set()

    def check(
        self,
        handler_id: EventHandlerId,
    ) -> EventHandlerRegistrationCheck:
        if handler_id in self._ids:
            return EventHandlerRegistrationConflict(handler_id)
        return EventHandlerRegistrationAvailable(handler_id)

    def register(
        self,
        definition: EventHandlerDefinition,
    ) -> EventHandlerRegistrationResult:
        if isinstance(
            self.check(definition.handler_id),
            EventHandlerRegistrationConflict,
        ):
            return EventHandlerRegistrationRejected(definition.handler_id)
        self._ids.add(definition.handler_id)
        self._definitions.append(definition)
        return EventHandlerRegistered(definition.handler_id)

    def matching(self, key: EventKey) -> EventHandlerMatchSet:
        exact_source_exact: list[EventHandlerDefinition] = []
        exact_source_pattern: list[EventHandlerDefinition] = []
        any_source_exact: list[EventHandlerDefinition] = []
        any_source_pattern: list[EventHandlerDefinition] = []

        for definition in self._definitions:
            if not isinstance(
                self._matcher.match(definition.pattern, key.name),
                EventPatternMatched,
            ):
                continue

            exact_pattern = isinstance(definition.pattern, ExactEventPattern)
            if isinstance(definition.source, ExactEventSource):
                if definition.source.app_id != key.app_id:
                    continue
                if exact_pattern:
                    exact_source_exact.append(definition)
                else:
                    exact_source_pattern.append(definition)
                continue

            if isinstance(definition.source, AnyEventSource):
                if exact_pattern:
                    any_source_exact.append(definition)
                else:
                    any_source_pattern.append(definition)
                continue

            raise AssertionError("unsupported event source selector")

        return EventHandlerMatchSet(
            definitions=tuple(
                exact_source_exact
                + exact_source_pattern
                + any_source_exact
                + any_source_pattern
            )
        )
