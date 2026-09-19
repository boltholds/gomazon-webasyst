from gomazon_webasyst.application.backend_session_bridge.composites.requests import (
    BackendPasswordLoginRequest,
)
from gomazon_webasyst.contracts.auth import (
    AuthenticationRejected,
    AuthenticationSucceeded,
)
from gomazon_webasyst.contracts.backend_session_bridge import (
    BackendPasswordLoginRejected,
    BackendPasswordLoginResult,
    BackendPasswordLoginSucceeded,
    IssueSessionCredential,
    KeepSessionCredential,
)
from gomazon_webasyst.contracts.enums import (
    BackendLoginPersistenceStatus,
    PersistentLoginMode,
    RememberIntent,
)
from gomazon_webasyst.contracts.persistent_login import (
    KeepPersistentCredential,
    PersistentCredentialIssueRejected,
    PersistentCredentialIssued,
    RefreshPersistentCredential,
)


class BackendPasswordLoginFlow:
    def __init__(
        self,
        *,
        authenticate_backend_password,
        issue_persistent_credential,
    ) -> None:
        self._authenticate_backend_password = authenticate_backend_password
        self._issue_persistent_credential = issue_persistent_credential

    async def __call__(
        self,
        request: BackendPasswordLoginRequest,
    ) -> BackendPasswordLoginResult:
        authenticated = await self._authenticate_backend_password(
            request.credentials
        )
        if isinstance(authenticated, AuthenticationRejected):
            return BackendPasswordLoginRejected(
                authentication_type=authenticated.type,
                session_disposition=KeepSessionCredential(),
                persistent_disposition=KeepPersistentCredential(),
            )
        if not isinstance(authenticated, AuthenticationSucceeded):
            raise AssertionError("unsupported backend authentication result")

        session_disposition = IssueSessionCredential(
            session_id=authenticated.session_key.session_id
        )

        if request.remember_intent is RememberIntent.SESSION_ONLY:
            return BackendPasswordLoginSucceeded(
                subject=authenticated.subject,
                session_disposition=session_disposition,
                persistent_disposition=KeepPersistentCredential(),
                persistence_status=BackendLoginPersistenceStatus.SESSION_ONLY,
            )

        if request.remember_intent is not RememberIntent.PERSIST:
            raise AssertionError("unsupported remember intent")

        if request.persistent_login_mode is PersistentLoginMode.DISABLED:
            return BackendPasswordLoginSucceeded(
                subject=authenticated.subject,
                session_disposition=session_disposition,
                persistent_disposition=KeepPersistentCredential(),
                persistence_status=BackendLoginPersistenceStatus.DISABLED,
            )
        if request.persistent_login_mode is not PersistentLoginMode.ENABLED:
            raise AssertionError("unsupported persistent login mode")

        issued = await self._issue_persistent_credential(authenticated.subject)
        if isinstance(issued, PersistentCredentialIssued):
            return BackendPasswordLoginSucceeded(
                subject=authenticated.subject,
                session_disposition=session_disposition,
                persistent_disposition=RefreshPersistentCredential(
                    credential=issued.credential,
                    lifetime=issued.lifetime,
                ),
                persistence_status=BackendLoginPersistenceStatus.ISSUED,
            )
        if isinstance(issued, PersistentCredentialIssueRejected):
            return BackendPasswordLoginSucceeded(
                subject=authenticated.subject,
                session_disposition=session_disposition,
                persistent_disposition=KeepPersistentCredential(),
                persistence_status=BackendLoginPersistenceStatus.UNAVAILABLE,
            )
        raise AssertionError("unsupported persistent credential issue result")
