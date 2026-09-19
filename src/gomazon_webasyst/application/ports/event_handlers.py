from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, TypeAlias

from gomazon_webasyst.application.events.vo.identity import EventHandlerId, EventKey
from gomazon_webasyst.application.events.vo.payload import (
    EventHandlerOutcome,
    EventPayload,
)

if TYPE_CHECKING:
    from gomazon_webasyst.application.events.entities.handler_definition import (
        EventHandlerDefinition,
    )


@dataclass(slots=True, frozen=True)
class EventHandlerContext:
    event: EventKey
    handler_id: EventHandlerId


class EventHandler(Protocol):
    async def handle(
        self,
        context: EventHandlerContext,
        payload: EventPayload,
    ) -> EventHandlerOutcome: ...


@dataclass(slots=True, frozen=True)
class EventHandlerRegistrationAvailable:
    handler_id: EventHandlerId


@dataclass(slots=True, frozen=True)
class EventHandlerRegistrationConflict:
    handler_id: EventHandlerId


EventHandlerRegistrationCheck: TypeAlias = (
    EventHandlerRegistrationAvailable | EventHandlerRegistrationConflict
)


@dataclass(slots=True, frozen=True)
class EventHandlerRegistered:
    handler_id: EventHandlerId


@dataclass(slots=True, frozen=True)
class EventHandlerRegistrationRejected:
    handler_id: EventHandlerId


EventHandlerRegistrationResult: TypeAlias = (
    EventHandlerRegistered | EventHandlerRegistrationRejected
)


@dataclass(slots=True, frozen=True)
class EventHandlerMatchSet:
    definitions: tuple["EventHandlerDefinition", ...]


class EventHandlerRegistry(Protocol):
    def check(
        self,
        handler_id: EventHandlerId,
    ) -> EventHandlerRegistrationCheck: ...

    def register(
        self,
        definition: "EventHandlerDefinition",
    ) -> EventHandlerRegistrationResult: ...

    def matching(self, key: EventKey) -> EventHandlerMatchSet: ...

