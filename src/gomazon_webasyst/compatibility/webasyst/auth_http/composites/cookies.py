from dataclasses import dataclass
from datetime import datetime
from typing import TypeAlias


@dataclass(slots=True, frozen=True)
class SetSessionCookie:
    value: str


@dataclass(slots=True, frozen=True)
class DeleteSessionCookie:
    pass


@dataclass(slots=True, frozen=True)
class KeepSessionCookie:
    pass


SessionCookieMutation: TypeAlias = (
    SetSessionCookie | DeleteSessionCookie | KeepSessionCookie
)


@dataclass(slots=True, frozen=True)
class SetPersistentCookie:
    value: str
    max_age_seconds: int
    expires_at: datetime

    def __post_init__(self) -> None:
        if self.max_age_seconds <= 0:
            raise ValueError("persistent cookie max age must be positive")


@dataclass(slots=True, frozen=True)
class DeletePersistentCookie:
    pass


@dataclass(slots=True, frozen=True)
class KeepPersistentCookie:
    pass


PersistentCookieMutation: TypeAlias = (
    SetPersistentCookie | DeletePersistentCookie | KeepPersistentCookie
)


@dataclass(slots=True, frozen=True)
class BackendAuthCookieMutations:
    session: SessionCookieMutation
    persistent: PersistentCookieMutation
