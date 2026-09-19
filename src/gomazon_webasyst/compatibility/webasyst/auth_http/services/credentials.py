from collections.abc import Mapping

from gomazon_webasyst.application.auth_values import SessionId
from gomazon_webasyst.application.backend_session_bridge.vo.credentials import (
    PersistentCredentialMissing,
    PersistentCredentialProvided,
    SessionCredentialMalformed,
    SessionCredentialMissing,
    SessionCredentialProvided,
)
from gomazon_webasyst.application.persistent_values import PersistentCredential
from gomazon_webasyst.compatibility.webasyst.auth_http.composites.request import (
    BackendAuthHttpCredentialState,
)
from gomazon_webasyst.compatibility.webasyst.auth_http.vo.cookies import (
    BackendAuthCookiePolicy,
)
from gomazon_webasyst.contracts.auth import SessionMetadata


class BackendAuthCredentialExtractionService:
    def extract(
        self,
        *,
        cookies: Mapping[str, str],
        user_agent: str,
        policy: BackendAuthCookiePolicy,
    ) -> BackendAuthHttpCredentialState:
        session_name = policy.session_name.value
        if session_name not in cookies:
            session_credential = SessionCredentialMissing()
        else:
            raw_session = cookies[session_name]
            session_credential = (
                SessionCredentialMalformed()
                if raw_session == ""
                else SessionCredentialProvided(SessionId(raw_session))
            )

        persistent_name = policy.persistent_name.value
        if persistent_name not in cookies or cookies[persistent_name] in {"", "0"}:
            persistent_credential = PersistentCredentialMissing()
        else:
            persistent_credential = PersistentCredentialProvided(
                PersistentCredential(cookies[persistent_name])
            )

        return BackendAuthHttpCredentialState(
            session_credential=session_credential,
            persistent_credential=persistent_credential,
            session_metadata=SessionMetadata(user_agent=user_agent),
        )
