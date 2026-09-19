from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.events.composites.contracts import (
    EventDispatchRequest,
)
from gomazon_webasyst.application.events.composites.dispatcher import (
    EventDispatcher,
)
from gomazon_webasyst.application.events.vo.identity import (
    EventKey,
    EventName,
)
from gomazon_webasyst.application.events.vo.payload import (
    EventHandlerOutcome,
    EventHandlerReturned,
    LegacyEventPayload,
)
from gomazon_webasyst.application.ports.event_handlers import (
    EventHandler,
    EventHandlerContext,
)


class TeamContactsCollectionBridge(EventHandler):
    def __init__(self, dispatcher: EventDispatcher) -> None:
        self._dispatcher = dispatcher

    async def handle(
        self,
        context: EventHandlerContext,
        payload: LegacyEventPayload,
    ) -> EventHandlerOutcome:
        report = await self._dispatcher.dispatch(
            EventDispatchRequest(
                event=EventKey(
                    AppId("team"),
                    EventName("contacts_collection"),
                ),
                payload=payload,
            )
        )
        return EventHandlerReturned(
            value=LegacyEventPayload(value=bool(report.results))
        )
