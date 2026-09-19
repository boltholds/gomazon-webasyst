from dataclasses import dataclass

from gomazon_webasyst.application.backend_session_bridge.vo.credentials import (
    PersistentCredentialInput,
    SessionCredentialInput,
)
from gomazon_webasyst.contracts.auth import (
    BackendPasswordCredentials,
    SessionMetadata,
)
from gomazon_webasyst.contracts.enums import PersistentLoginMode, RememberIntent


@dataclass(slots=True, frozen=True)
class BackendCurrentSubjectRequest:
    session_credential: SessionCredentialInput
    persistent_credential: PersistentCredentialInput
    session_metadata: SessionMetadata
    persistent_login_mode: PersistentLoginMode


@dataclass(slots=True, frozen=True)
class BackendPasswordLoginRequest:
    credentials: BackendPasswordCredentials
    remember_intent: RememberIntent
    persistent_login_mode: PersistentLoginMode


@dataclass(slots=True, frozen=True)
class BackendLogoutRequest:
    session_credential: SessionCredentialInput
