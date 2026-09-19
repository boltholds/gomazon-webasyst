from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.application.auth_values import SessionId
from gomazon_webasyst.application.persistent_values import PersistentCredential


@dataclass(slots=True, frozen=True)
class SessionCredentialMissing:
    pass


@dataclass(slots=True, frozen=True)
class SessionCredentialMalformed:
    pass


@dataclass(slots=True, frozen=True)
class SessionCredentialProvided:
    session_id: SessionId


SessionCredentialInput: TypeAlias = (
    SessionCredentialMissing
    | SessionCredentialMalformed
    | SessionCredentialProvided
)


@dataclass(slots=True, frozen=True)
class PersistentCredentialMissing:
    pass


@dataclass(slots=True, frozen=True)
class PersistentCredentialProvided:
    credential: PersistentCredential


PersistentCredentialInput: TypeAlias = (
    PersistentCredentialMissing | PersistentCredentialProvided
)
