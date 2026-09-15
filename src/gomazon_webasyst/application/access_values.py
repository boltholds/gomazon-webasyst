from dataclasses import dataclass
from typing import TypeAlias


@dataclass(slots=True, frozen=True)
class GroupId:
    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("group id must be positive")


@dataclass(slots=True, frozen=True)
class AppId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("app id must not be empty")
        if len(self.value) > 32:
            raise ValueError("app id must not exceed 32 characters")


@dataclass(slots=True, frozen=True)
class RightName:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("right name must not be empty")
        if len(self.value) > 64:
            raise ValueError("right name must not exceed 64 characters")


@dataclass(slots=True, frozen=True)
class RightValue:
    value: int


@dataclass(slots=True, frozen=True)
class PermissionKey:
    app_id: AppId
    name: RightName


@dataclass(slots=True, frozen=True)
class UserTarget:
    contact_id: int

    def __post_init__(self) -> None:
        if self.contact_id <= 0:
            raise ValueError("contact id must be positive")


@dataclass(slots=True, frozen=True)
class GroupTarget:
    group_id: GroupId


@dataclass(slots=True, frozen=True)
class GuestsTarget:
    pass


AccessTarget: TypeAlias = UserTarget | GroupTarget | GuestsTarget


@dataclass(slots=True, frozen=True)
class GroupMembership:
    contact_id: int
    group_id: GroupId

    def __post_init__(self) -> None:
        if self.contact_id <= 0:
            raise ValueError("contact id must be positive")
