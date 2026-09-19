from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.events.composites.contracts import (
    EventDispatchRequest,
)
from gomazon_webasyst.application.events.vo.identity import EventKey, EventName
from gomazon_webasyst.application.events.vo.payload import (
    EventHandlerNoResult,
    EventPayload,
)
from gomazon_webasyst.application.ports.event_handlers import EventHandlerContext
from gomazon_webasyst.application.ports.event_publisher import EventPublisher


_TEAM_CONTACTS_DELETE = EventKey(
    app_id=AppId("team"),
    name=EventName("contacts_delete"),
)


class TeamContactsDeleteRelayHandler:
    def __init__(self, event_publisher: EventPublisher) -> None:
        self._event_publisher = event_publisher

    async def handle(
        self,
        context: EventHandlerContext,
        payload: EventPayload,
    ) -> EventHandlerNoResult:
        await self._event_publisher.publish(
            EventDispatchRequest(
                event=_TEAM_CONTACTS_DELETE,
                payload=payload,
            )
        )
        return EventHandlerNoResult()
