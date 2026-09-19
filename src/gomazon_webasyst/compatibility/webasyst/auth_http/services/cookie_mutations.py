from collections.abc import Callable
from datetime import datetime

from gomazon_webasyst.compatibility.webasyst.auth_http.composites.cookies import (
    BackendAuthCookieMutations,
    DeletePersistentCookie,
    DeleteSessionCookie,
    KeepPersistentCookie,
    KeepSessionCookie,
    SetPersistentCookie,
    SetSessionCookie,
)
from gomazon_webasyst.contracts.backend_session_bridge import (
    ClearSessionCredential,
    IssueSessionCredential,
    KeepSessionCredential,
    SessionCredentialDisposition,
)
from gomazon_webasyst.contracts.persistent_login import (
    ClearPersistentCredential,
    KeepPersistentCredential,
    PersistentCredentialDisposition,
    RefreshPersistentCredential,
)


class BackendAuthCookieMutationService:
    def __init__(self, *, clock: Callable[[], datetime]) -> None:
        self._clock = clock

    def plan(
        self,
        *,
        session_disposition: SessionCredentialDisposition,
        persistent_disposition: PersistentCredentialDisposition,
    ) -> BackendAuthCookieMutations:
        if isinstance(session_disposition, IssueSessionCredential):
            session = SetSessionCookie(session_disposition.session_id.value)
        elif isinstance(session_disposition, ClearSessionCredential):
            session = DeleteSessionCookie()
        elif isinstance(session_disposition, KeepSessionCredential):
            session = KeepSessionCookie()
        else:
            raise AssertionError("unsupported session credential disposition")

        if isinstance(persistent_disposition, RefreshPersistentCredential):
            lifetime = persistent_disposition.lifetime.value
            max_age_seconds = int(lifetime.total_seconds())
            if max_age_seconds <= 0:
                raise ValueError("persistent credential lifetime must be positive")
            persistent = SetPersistentCookie(
                value=persistent_disposition.credential.value,
                max_age_seconds=max_age_seconds,
                expires_at=self._clock() + lifetime,
            )
        elif isinstance(persistent_disposition, ClearPersistentCredential):
            persistent = DeletePersistentCookie()
        elif isinstance(persistent_disposition, KeepPersistentCredential):
            persistent = KeepPersistentCookie()
        else:
            raise AssertionError("unsupported persistent credential disposition")

        return BackendAuthCookieMutations(
            session=session,
            persistent=persistent,
        )
