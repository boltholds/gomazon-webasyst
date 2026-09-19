from dataclasses import dataclass

from gomazon_webasyst.application.access_values import AppId


@dataclass(slots=True, frozen=True)
class EventName:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("event name must not be empty")


@dataclass(slots=True, frozen=True)
class EventHandlerId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("event handler id must not be empty")


@dataclass(slots=True, frozen=True)
class EventKey:
    app_id: AppId
    name: EventName
