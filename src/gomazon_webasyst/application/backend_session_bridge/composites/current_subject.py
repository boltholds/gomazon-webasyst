from gomazon_webasyst.application.backend_session_bridge.composites.requests import (
    BackendCurrentSubjectRequest,
)
from gomazon_webasyst.application.backend_session_bridge.vo.credentials import (
    PersistentCredentialMissing,
    PersistentCredentialProvided,
    SessionCredentialMalformed,
    SessionCredentialMissing,
    SessionCredentialProvided,
)
from gomazon_webasyst.contracts.auth import SessionResolutionError, SessionResolved
from gomazon_webasyst.contracts.backend_session_bridge import (
    ClearSessionCredential,
    CurrentBackendSubjectResolved,
    CurrentBackendSubjectResult,
    CurrentBackendSubjectUnauthenticated,
    IssueSessionCredential,
    KeepSessionCredential,
)
from gomazon_webasyst.contracts.enums import (
    CurrentBackendSubjectReason,
    PersistentLoginMode,
    PersistentLoginRejectReason,
)
from gomazon_webasyst.contracts.persistent_login import (
    KeepPersistentCredential,
    PersistentLoginRejected,
    PersistentLoginRequest,
    PersistentLoginRestored,
)


class BackendCurrentSubjectFlow:
    def __init__(
        self,
        *,
        resolve_backend_session,
        restore_backend_session_from_persistent_credential,
    ) -> None:
        self._resolve_backend_session = resolve_backend_session
        self._restore_backend_session_from_persistent_credential = (
            restore_backend_session_from_persistent_credential
        )

    async def __call__(
        self,
        request: BackendCurrentSubjectRequest,
    ) -> CurrentBackendSubjectResult:
        session_disposition = KeepSessionCredential()
        unresolved_reason = CurrentBackendSubjectReason.NO_CREDENTIAL

        if isinstance(request.session_credential, SessionCredentialProvided):
            session_result = await self._resolve_backend_session(
                request.session_credential.session_id
            )
            if isinstance(session_result, SessionResolved):
                return CurrentBackendSubjectResolved(
                    subject=session_result.subject,
                    session_disposition=KeepSessionCredential(),
                    persistent_disposition=KeepPersistentCredential(),
                )
            if not isinstance(session_result, SessionResolutionError):
                raise AssertionError("unsupported backend session resolution")
            session_disposition = ClearSessionCredential()
            unresolved_reason = CurrentBackendSubjectReason.SESSION_REJECTED
        elif isinstance(request.session_credential, SessionCredentialMalformed):
            session_disposition = ClearSessionCredential()
            unresolved_reason = CurrentBackendSubjectReason.SESSION_REJECTED
        elif not isinstance(request.session_credential, SessionCredentialMissing):
            raise AssertionError("unsupported session credential input")

        if request.persistent_login_mode is PersistentLoginMode.DISABLED:
            return CurrentBackendSubjectUnauthenticated(
                reason=unresolved_reason,
                session_disposition=session_disposition,
                persistent_disposition=KeepPersistentCredential(),
            )

        if isinstance(request.persistent_credential, PersistentCredentialMissing):
            return CurrentBackendSubjectUnauthenticated(
                reason=unresolved_reason,
                session_disposition=session_disposition,
                persistent_disposition=KeepPersistentCredential(),
            )
        if not isinstance(request.persistent_credential, PersistentCredentialProvided):
            raise AssertionError("unsupported persistent credential input")

        restored = await self._restore_backend_session_from_persistent_credential(
            PersistentLoginRequest(
                credential=request.persistent_credential.credential,
                session_metadata=request.session_metadata,
            )
        )
        if isinstance(restored, PersistentLoginRestored):
            return CurrentBackendSubjectResolved(
                subject=restored.subject,
                session_disposition=IssueSessionCredential(
                    session_id=restored.session_key.session_id
                ),
                persistent_disposition=restored.credential_disposition,
            )
        if not isinstance(restored, PersistentLoginRejected):
            raise AssertionError("unsupported persistent login result")

        reason = (
            CurrentBackendSubjectReason.SESSION_UNAVAILABLE
            if restored.reason is PersistentLoginRejectReason.SESSION_UNAVAILABLE
            else CurrentBackendSubjectReason.PERSISTENT_REJECTED
        )
        return CurrentBackendSubjectUnauthenticated(
            reason=reason,
            session_disposition=session_disposition,
            persistent_disposition=restored.credential_disposition,
        )
