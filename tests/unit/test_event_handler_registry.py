import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.events.entities.handler_definition import (
    EventHandlerDefinition,
)
from gomazon_webasyst.application.events.services.pattern_matcher import (
    EventPatternMatcher,
    EventPatternNotMatched,
)
from gomazon_webasyst.application.events.vo.identity import (
    EventHandlerId,
    EventKey,
    EventName,
)
from gomazon_webasyst.application.events.vo.owners import ApplicationEventOwner
from gomazon_webasyst.application.events.vo.patterns import (
    AnyEventSource,
    EventNamePrefix,
    ExactEventPattern,
    ExactEventSource,
    PrefixEventPattern,
)
from gomazon_webasyst.application.events.vo.payload import EventHandlerNoResult
from gomazon_webasyst.application.ports.event_handlers import (
    EventHandlerContext,
    EventHandlerRegistered,
    EventHandlerRegistrationRejected,
)
from gomazon_webasyst.infrastructure.events.registry import (
    InMemoryEventHandlerRegistry,
)


class RejectRegex:
    def match(self, expression, event_name):
        return EventPatternNotMatched()


class Handler:
    async def handle(self, context: EventHandlerContext, payload):
        return EventHandlerNoResult()


def _definition(
    handler_id: str,
    *,
    source,
    pattern,
) -> EventHandlerDefinition:
    return EventHandlerDefinition(
        handler_id=EventHandlerId(handler_id),
        owner=ApplicationEventOwner(AppId("consumer")),
        source=source,
        pattern=pattern,
        handler=Handler(),
    )


def _registry() -> InMemoryEventHandlerRegistry:
    return InMemoryEventHandlerRegistry(
        EventPatternMatcher(RejectRegex())
    )


def test_registry_rejects_duplicate_handler_identity() -> None:
    registry = _registry()
    definition = _definition(
        "same",
        source=ExactEventSource(AppId("shop")),
        pattern=ExactEventPattern(EventName("backend_order")),
    )
    assert isinstance(registry.register(definition), EventHandlerRegistered)
    assert isinstance(
        registry.register(definition),
        EventHandlerRegistrationRejected,
    )


def test_matching_preserves_legacy_four_bucket_precedence() -> None:
    registry = _registry()
    definitions = (
        _definition(
            "any-pattern-1",
            source=AnyEventSource(),
            pattern=PrefixEventPattern(EventNamePrefix("backend_")),
        ),
        _definition(
            "any-exact",
            source=AnyEventSource(),
            pattern=ExactEventPattern(EventName("backend_order")),
        ),
        _definition(
            "exact-pattern-1",
            source=ExactEventSource(AppId("shop")),
            pattern=PrefixEventPattern(EventNamePrefix("backend_")),
        ),
        _definition(
            "exact-exact-1",
            source=ExactEventSource(AppId("shop")),
            pattern=ExactEventPattern(EventName("backend_order")),
        ),
        _definition(
            "exact-pattern-2",
            source=ExactEventSource(AppId("shop")),
            pattern=PrefixEventPattern(EventNamePrefix("backend_")),
        ),
        _definition(
            "exact-exact-2",
            source=ExactEventSource(AppId("shop")),
            pattern=ExactEventPattern(EventName("backend_order")),
        ),
        _definition(
            "any-pattern-2",
            source=AnyEventSource(),
            pattern=PrefixEventPattern(EventNamePrefix("backend_")),
        ),
    )
    for definition in definitions:
        registry.register(definition)

    matched = registry.matching(
        EventKey(AppId("shop"), EventName("backend_order"))
    )
    assert tuple(d.handler_id.value for d in matched.definitions) == (
        "exact-exact-1",
        "exact-exact-2",
        "exact-pattern-1",
        "exact-pattern-2",
        "any-exact",
        "any-pattern-1",
        "any-pattern-2",
    )


def test_nonmatching_source_or_pattern_is_omitted() -> None:
    registry = _registry()
    registry.register(
        _definition(
            "wrong-source",
            source=ExactEventSource(AppId("blog")),
            pattern=ExactEventPattern(EventName("backend_order")),
        )
    )
    registry.register(
        _definition(
            "wrong-event",
            source=ExactEventSource(AppId("shop")),
            pattern=ExactEventPattern(EventName("frontend_order")),
        )
    )
    assert registry.matching(
        EventKey(AppId("shop"), EventName("backend_order"))
    ).definitions == ()
