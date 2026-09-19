import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.events.composites.contracts import (
    EventDispatchRequest,
)
from gomazon_webasyst.application.events.composites.dispatcher import EventDispatcher
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
from gomazon_webasyst.application.events.vo.owners import (
    ApplicationEventOwner,
    PluginEventOwner,
)
from gomazon_webasyst.application.events.vo.patterns import (
    ExactEventPattern,
    ExactEventSource,
)
from gomazon_webasyst.application.events.vo.payload import (
    EventHandlerNoResult,
    EventHandlerReturned,
    LegacyEventPayload,
)
from gomazon_webasyst.application.plugins.vo.identity import PluginId, PluginKey
from gomazon_webasyst.infrastructure.events.registry import (
    InMemoryEventHandlerRegistry,
)


class RejectRegex:
    def match(self, expression, event_name):
        return EventPatternNotMatched()


class RecordingHandler:
    def __init__(self, name: str, calls: list[str], outcome) -> None:
        self._name = name
        self._calls = calls
        self._outcome = outcome

    async def handle(self, context, payload):
        self._calls.append(self._name)
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome


def _registry() -> InMemoryEventHandlerRegistry:
    return InMemoryEventHandlerRegistry(
        EventPatternMatcher(RejectRegex())
    )


def _definition(
    handler_id: str,
    owner,
    handler,
) -> EventHandlerDefinition:
    return EventHandlerDefinition(
        handler_id=EventHandlerId(handler_id),
        owner=owner,
        source=ExactEventSource(AppId("shop")),
        pattern=ExactEventPattern(EventName("order.saved")),
        handler=handler,
    )


@pytest.mark.asyncio
async def test_no_result_leaves_owner_open_then_first_return_closes_it() -> None:
    calls: list[str] = []
    owner = ApplicationEventOwner(AppId("blog"))
    registry = _registry()
    registry.register(
        _definition(
            "first",
            owner,
            RecordingHandler("first", calls, EventHandlerNoResult()),
        )
    )
    registry.register(
        _definition(
            "second",
            owner,
            RecordingHandler(
                "second",
                calls,
                EventHandlerReturned(
                    value=LegacyEventPayload(value={"value": 2})
                ),
            ),
        )
    )
    registry.register(
        _definition(
            "third",
            owner,
            RecordingHandler(
                "third",
                calls,
                EventHandlerReturned(
                    value=LegacyEventPayload(value={"value": 3})
                ),
            ),
        )
    )

    report = await EventDispatcher(registry).dispatch(
        EventDispatchRequest(
            event=EventKey(AppId("shop"), EventName("order.saved")),
            payload=LegacyEventPayload(value={"order_id": 7}),
        )
    )

    assert calls == ["first", "second"]
    assert len(report.results) == 1
    assert report.results[0].handler_id == EventHandlerId("second")
    assert report.results[0].value.value == {"value": 2}


@pytest.mark.asyncio
async def test_different_owners_each_keep_first_result() -> None:
    calls: list[str] = []
    app_owner = ApplicationEventOwner(AppId("blog"))
    plugin_owner = PluginEventOwner(
        PluginKey(AppId("site"), PluginId("demo"))
    )
    registry = _registry()
    for definition in (
        _definition(
            "app",
            app_owner,
            RecordingHandler(
                "app",
                calls,
                EventHandlerReturned(value=LegacyEventPayload(value="app")),
            ),
        ),
        _definition(
            "plugin",
            plugin_owner,
            RecordingHandler(
                "plugin",
                calls,
                EventHandlerReturned(value=LegacyEventPayload(value="plugin")),
            ),
        ),
    ):
        registry.register(definition)

    report = await EventDispatcher(registry).dispatch(
        EventDispatchRequest(
            event=EventKey(AppId("shop"), EventName("order.saved")),
            payload=LegacyEventPayload(value={}),
        )
    )

    assert calls == ["app", "plugin"]
    assert tuple(result.value.value for result in report.results) == (
        "app",
        "plugin",
    )


@pytest.mark.asyncio
async def test_handler_exception_is_diagnostic_and_dispatch_continues() -> None:
    calls: list[str] = []
    failing_owner = ApplicationEventOwner(AppId("blog"))
    healthy_owner = ApplicationEventOwner(AppId("site"))
    registry = _registry()
    registry.register(
        _definition(
            "bad",
            failing_owner,
            RecordingHandler("bad", calls, RuntimeError("boom")),
        )
    )
    registry.register(
        _definition(
            "good",
            healthy_owner,
            RecordingHandler(
                "good",
                calls,
                EventHandlerReturned(value=LegacyEventPayload(value="ok")),
            ),
        )
    )

    report = await EventDispatcher(registry).dispatch(
        EventDispatchRequest(
            event=EventKey(AppId("shop"), EventName("order.saved")),
            payload=LegacyEventPayload(value={}),
        )
    )

    assert calls == ["bad", "good"]
    assert tuple(result.value.value for result in report.results) == ("ok",)
    assert len(report.failures) == 1
    assert report.failures[0].handler_id == EventHandlerId("bad")
    assert report.failures[0].error_type == "RuntimeError"
    assert report.failures[0].message == "boom"
