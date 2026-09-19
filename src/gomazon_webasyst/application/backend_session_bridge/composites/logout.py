from gomazon_webasyst.application.backend_session_bridge.composites.requests import (
    BackendLogoutRequest,
)
from gomazon_webasyst.application.backend_session_bridge.vo.credentials import (
    SessionCredentialMalformed,
    SessionCredentialMissing,
    SessionCredentialProvided,
)
from gomazon_webasyst.contracts.auth import LogoutResult
from gomazon_webasyst.contracts.backend_session_bridge import (
    BackendLogoutCompleted,
    BackendLogoutResult,
    ClearSessionCredential,
)
from gomazon_webasyst.contracts.enums import LogoutStatus
from gomazon_webasyst.contracts.persistent_login import ClearPersistentCredential


class BackendLogoutFlow:
    def __init__(
        self,
        *,
        logout_backend_session,
        revoke_persistent_credential,
    ) -> None:
        self._logout_backend_session = logout_backend_session
        self._revoke_persistent_credential = revoke_persistent_credential

    async def __call__(
        self,
        request: BackendLogoutRequest,
    ) -> BackendLogoutResult:
        if isinstance(request.session_credential, SessionCredentialProvided):
            logout_result = await self._logout_backend_session(
                request.session_credential.session_id
            )
            if not isinstance(logout_result, LogoutResult):
                raise AssertionError("unsupported backend logout result")
            session_status = logout_result.status
        elif isinstance(
            request.session_credential,
            SessionCredentialMissing | SessionCredentialMalformed,
        ):
            session_status = LogoutStatus.ALREADY_MISSING
        else:
            raise AssertionError("unsupported session credential input")

        persistent_disposition = await self._revoke_persistent_credential()
        if not isinstance(persistent_disposition, ClearPersistentCredential):
            raise AssertionError("unsupported persistent revoke disposition")

        return BackendLogoutCompleted(
            session_status=session_status,
            session_disposition=ClearSessionCredential(),
            persistent_disposition=persistent_disposition,
        )
