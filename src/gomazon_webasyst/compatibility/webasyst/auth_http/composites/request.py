from dataclasses import dataclass

from gomazon_webasyst.application.backend_session_bridge.vo.credentials import (
    PersistentCredentialInput,
    SessionCredentialInput,
)
from gomazon_webasyst.contracts.auth import SessionMetadata


@dataclass(slots=True, frozen=True)
class BackendAuthHttpCredentialState:
    session_credential: SessionCredentialInput
    persistent_credential: PersistentCredentialInput
    session_metadata: SessionMetadata
