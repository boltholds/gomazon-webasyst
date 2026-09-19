from dataclasses import dataclass

from gomazon_webasyst.application.events.vo.identity import EventHandlerId
from gomazon_webasyst.application.events.vo.owners import EventHandlerOwner
from gomazon_webasyst.application.events.vo.patterns import (
    EventNamePattern,
    EventSourceSelector,
)
from gomazon_webasyst.application.ports.event_handlers import EventHandler


@dataclass(slots=True, frozen=True)
class EventHandlerDefinition:
    handler_id: EventHandlerId
    owner: EventHandlerOwner
    source: EventSourceSelector
    pattern: EventNamePattern
    handler: EventHandler
