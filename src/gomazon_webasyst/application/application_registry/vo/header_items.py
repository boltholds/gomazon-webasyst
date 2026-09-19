from dataclasses import dataclass

from gomazon_webasyst.application.application_registry.vo.icons import (
    ApplicationIconSet,
)
from gomazon_webasyst.application.application_registry.vo.metadata import (
    ApplicationDisplayName,
)


@dataclass(slots=True, frozen=True)
class ApplicationHeaderItemId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("application header item id must not be empty")


@dataclass(slots=True, frozen=True)
class ApplicationHeaderItem:
    item_id: ApplicationHeaderItemId
    display_name: ApplicationDisplayName
    icons: ApplicationIconSet


@dataclass(slots=True, frozen=True)
class ApplicationHeaderItems:
    items: tuple[ApplicationHeaderItem, ...]

    def __post_init__(self) -> None:
        ids = [item.item_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate application header item id")
