import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.events.composites.contracts import (
    EventDispatchReport,
)
from gomazon_webasyst.application.events.vo.identity import (
    EventHandlerId,
    EventKey,
    EventName,
)
from gomazon_webasyst.application.events.vo.payload import (
    EventHandlerNoResult,
    LegacyEventPayload,
)
from gomazon_webasyst.application.ports.event_handlers import EventHandlerContext
from gomazon_webasyst.compatibility.webasyst.team.events import (
    TeamContactsDeleteRelayHandler,
)


class RecordingPublisher:
    def __init__(self) -> None:
        self.requests = []

    async def publish(self, request):
        self.requests.append(request)
        return EventDispatchReport(
            event=request.event,
            results=(),
            failures=(),
        )


@pytest.mark.asyncio
async def test_team_contacts_delete_relay_publishes_team_event_with_same_payload() -> None:
    publisher = RecordingPublisher()
    handler = TeamContactsDeleteRelayHandler(publisher)
    payload = LegacyEventPayload(value={"id": (7, 8)})
    context = EventHandlerContext(
        event=EventKey(AppId("contacts"), EventName("delete")),
        handler_id=EventHandlerId("team-contacts-delete-relay"),
    )

    outcome = await handler.handle(context, payload)

    assert isinstance(outcome, EventHandlerNoResult)
    assert len(publisher.requests) == 1
    nested = publisher.requests[0]
    assert nested.event == EventKey(
        AppId("team"),
        EventName("contacts_delete"),
    )
    assert nested.payload is payload
