from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from gomazon_webasyst.application.backend_session_bridge.composites.current_subject import (
    BackendCurrentSubjectFlow,
)
from gomazon_webasyst.application.backend_session_bridge.composites.login import (
    BackendPasswordLoginFlow,
)
from gomazon_webasyst.application.backend_session_bridge.composites.logout import (
    BackendLogoutFlow,
)
from gomazon_webasyst.compatibility.webasyst.auth_http.services.cookie_mutations import (
    BackendAuthCookieMutationService,
)
from gomazon_webasyst.compatibility.webasyst.auth_http.services.credentials import (
    BackendAuthCredentialExtractionService,
)
from gomazon_webasyst.compatibility.webasyst.auth_http.vo.cookies import (
    BackendAuthCookiePolicy,
    CookieName,
)
from gomazon_webasyst.composition.auth import AuthUseCases
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.contracts.enums import CookieSameSite, PersistentLoginMode


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True, frozen=True)
class BackendSessionBridgeComponents:
    current_subject_flow: BackendCurrentSubjectFlow
    password_login_flow: BackendPasswordLoginFlow
    logout_flow: BackendLogoutFlow
    credential_extractor: BackendAuthCredentialExtractionService
    cookie_mutation_service: BackendAuthCookieMutationService
    cookie_policy: BackendAuthCookiePolicy
    persistent_login_mode: PersistentLoginMode


def create_backend_session_bridge_components(
    auth: AuthUseCases,
    settings: Settings,
    *,
    clock: Callable[[], datetime] = _utc_now,
) -> BackendSessionBridgeComponents:
    cookie_policy = BackendAuthCookiePolicy(
        session_name=CookieName(settings.backend_session_cookie_name),
        persistent_name=CookieName(settings.persistent_auth_cookie_name),
        secure=settings.backend_auth_cookie_secure,
        path="/",
        same_site=CookieSameSite.LAX,
    )
    mode = (
        PersistentLoginMode.ENABLED
        if settings.persistent_login_enabled
        else PersistentLoginMode.DISABLED
    )
    return BackendSessionBridgeComponents(
        current_subject_flow=BackendCurrentSubjectFlow(
            resolve_backend_session=auth.resolve_backend_session,
            restore_backend_session_from_persistent_credential=(
                auth.restore_backend_session_from_persistent_credential
            ),
        ),
        password_login_flow=BackendPasswordLoginFlow(
            authenticate_backend_password=auth.authenticate_backend_password,
            issue_persistent_credential=auth.issue_persistent_credential,
        ),
        logout_flow=BackendLogoutFlow(
            logout_backend_session=auth.logout_backend_session,
            revoke_persistent_credential=auth.revoke_persistent_credential,
        ),
        credential_extractor=BackendAuthCredentialExtractionService(),
        cookie_mutation_service=BackendAuthCookieMutationService(clock=clock),
        cookie_policy=cookie_policy,
        persistent_login_mode=mode,
    )
