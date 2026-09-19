from typing import Protocol

from gomazon_webasyst.application.events.composites.contracts import (
    EventDispatchReport,
    EventDispatchRequest,
)


class EventPublisher(Protocol):
    async def publish(
        self,
        request: EventDispatchRequest,
    ) -> EventDispatchReport: ...
