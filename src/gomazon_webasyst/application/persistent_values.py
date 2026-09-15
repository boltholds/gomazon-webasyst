from dataclasses import dataclass
from datetime import timedelta


@dataclass(slots=True, frozen=True)
class PersistentCredential:
    value: str


@dataclass(slots=True, frozen=True)
class PersistentCredentialLifetime:
    value: timedelta
