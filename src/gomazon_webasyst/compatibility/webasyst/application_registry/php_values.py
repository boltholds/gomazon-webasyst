from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


@dataclass(slots=True, frozen=True)
class PhpNull:
    pass


@dataclass(slots=True, frozen=True)
class PhpArrayAutoKey:
    pass


@dataclass(slots=True, frozen=True)
class PhpArrayStringKey:
    value: str


@dataclass(slots=True, frozen=True)
class PhpArrayIntKey:
    value: int


PhpArrayKey: TypeAlias = PhpArrayAutoKey | PhpArrayStringKey | PhpArrayIntKey


@dataclass(slots=True, frozen=True)
class PhpArrayEntry:
    key: PhpArrayKey
    value: PhpValue


@dataclass(slots=True, frozen=True)
class PhpArray:
    entries: tuple[PhpArrayEntry, ...]


PhpValue: TypeAlias = str | int | float | bool | PhpNull | PhpArray
