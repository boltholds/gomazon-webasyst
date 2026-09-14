from dataclasses import dataclass
from typing import Protocol

from gomazon_webasyst.contracts.auth import StoredAuthSession
from gomazon_webasyst.contracts.enums import EnumStr


class SessionValidationDecision(EnumStr):
    VALIDATE = "validate"
    TRUST_STORED = "trust_stored"


class SessionValidationPolicy(Protocol):
    def decide(self, state: StoredAuthSession) -> SessionValidationDecision: ...


@dataclass(slots=True, frozen=True)
class StrictSessionValidationPolicy:
    def decide(self, state: StoredAuthSession) -> SessionValidationDecision:
        return SessionValidationDecision.VALIDATE
