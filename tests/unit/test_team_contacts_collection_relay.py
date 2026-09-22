import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.events.composites.contracts import (
    EventDispatchReport,
    EventDispatchResult,
    EventHandlerFailureDiagnostic,
)
from gomazon_webasyst.application.events.vo.identity import (
    EventHandlerId,
    EventKey,
    EventName,
)
from gomazon_webasyst.application.events.vo.owners import ApplicationEventOwner
from gomazon_webasyst.application.events.vo.payload import (
    EventHandlerReturned,
    LegacyEventPayload,
)
from gomazon_webasyst.application.ports.event_handlers import EventHandlerContext
from gomazon_webasyst.compatibility.webasyst.team.events import (
    TeamContactsCollectionRelayHandler,
)


class FixedReportPublisher:
    def __init__(self, report_factory) -> None:
        self._report_factory = report_factory
        self.requests = []

    async def publish(self, request):
        self.requests.append(request)
        return self._report_factory(request)


def _context() -> EventHandlerContext:
    return EventHandlerContext(
        event=EventKey(
            AppId("contacts"),
            EventName("contacts_collection"),
        ),
        handler_id=EventHandlerId("team-contacts-collection-relay"),
    )


def _empty_report(request):
    return EventDispatchReport(
        event=request.event,
        results=(),
        failures=(),
    )


@pytest.mark.asyncio
async def test_contacts_collection_relay_returns_false_when_nested_has_no_result() -> None:
    publisher = FixedReportPublisher(_empty_report)
    handler = TeamContactsCollectionRelayHandler(publisher)
    payload = LegacyEventPayload(value={"hash": "users"})

    outcome = await handler.handle(_context(), payload)

    assert isinstance(outcome, EventHandlerReturned)
    assert isinstance(outcome.value, LegacyEventPayload)
    assert outcome.value.value is False
    assert len(publisher.requests) == 1
    nested = publisher.requests[0]
    assert nested.event == EventKey(
        AppId("team"),
        EventName("contacts_collection"),
    )
    assert nested.payload is payload


@pytest.mark.asyncio
async def test_contacts_collection_relay_uses_result_presence_not_payload_truthiness() -> None:
    def report(request):
        return EventDispatchReport(
            event=request.event,
            results=(
                EventDispatchResult(
                    handler_id=EventHandlerId("nested"),
                    owner=ApplicationEventOwner(AppId("audit")),
                    value=LegacyEventPayload(value=False),
                ),
            ),
            failures=(),
        )

    publisher = FixedReportPublisher(report)
    handler = TeamContactsCollectionRelayHandler(publisher)

    outcome = await handler.handle(
        _context(),
        LegacyEventPayload(value={"hash": "users"}),
    )

    assert isinstance(outcome, EventHandlerReturned)
    assert outcome.value == LegacyEventPayload(value=True)


@pytest.mark.asyncio
async def test_contacts_collection_relay_failure_without_result_returns_false() -> None:
    def report(request):
        return EventDispatchReport(
            event=request.event,
            results=(),
            failures=(
                EventHandlerFailureDiagnostic(
                    handler_id=EventHandlerId("broken"),
                    owner=ApplicationEventOwner(AppId("audit")),
                    error_type="RuntimeError",
                    message="boom",
                ),
            ),
        )

    publisher = FixedReportPublisher(report)
    handler = TeamContactsCollectionRelayHandler(publisher)

    outcome = await handler.handle(
        _context(),
        LegacyEventPayload(value={"hash": "users"}),
    )

    assert isinstance(outcome, EventHandlerReturned)
    assert outcome.value == LegacyEventPayload(value=False)
