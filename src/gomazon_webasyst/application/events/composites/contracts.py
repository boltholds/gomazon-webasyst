from dataclasses import dataclass

from gomazon_webasyst.application.events.vo.identity import EventHandlerId, EventKey
from gomazon_webasyst.application.events.vo.owners import EventHandlerOwner
from gomazon_webasyst.application.events.vo.payload import EventPayload


@dataclass(slots=True, frozen=True)
class EventDispatchRequest:
    event: EventKey
    payload: EventPayload


@dataclass(slots=True, frozen=True)
class EventDispatchResult:
    handler_id: EventHandlerId
    owner: EventHandlerOwner
    value: EventPayload


@dataclass(slots=True, frozen=True)
class EventHandlerFailureDiagnostic:
    handler_id: EventHandlerId
    owner: EventHandlerOwner
    error_type: str
    message: str

    def __post_init__(self) -> None:
        if not self.error_type:
            raise ValueError("event handler failure error type must not be empty")


@dataclass(slots=True, frozen=True)
class EventDispatchReport:
    event: EventKey
    results: tuple[EventDispatchResult, ...]
    failures: tuple[EventHandlerFailureDiagnostic, ...]
