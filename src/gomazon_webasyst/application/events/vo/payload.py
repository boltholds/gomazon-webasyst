from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, JsonValue


class EventPayload(BaseModel):
    model_config = ConfigDict(frozen=True)


class LegacyEventPayload(EventPayload):
    value: JsonValue


class EventHandlerNoResult(BaseModel):
    model_config = ConfigDict(frozen=True)


class EventHandlerReturned(BaseModel):
    model_config = ConfigDict(frozen=True)

    value: EventPayload


EventHandlerOutcome: TypeAlias = EventHandlerNoResult | EventHandlerReturned
