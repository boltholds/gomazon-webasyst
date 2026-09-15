from dataclasses import dataclass
from typing import Protocol, TypeAlias


@dataclass(slots=True, frozen=True)
class AccessSubjectResolved:
    contact_id: int


@dataclass(slots=True, frozen=True)
class AccessSubjectMissing:
    contact_id: int


@dataclass(slots=True, frozen=True)
class AccessSubjectNotUser:
    contact_id: int


AccessSubjectResolution: TypeAlias = (
    AccessSubjectResolved | AccessSubjectMissing | AccessSubjectNotUser
)


class AccessSubjectStore(Protocol):
    async def resolve(self, contact_id: int) -> AccessSubjectResolution: ...
