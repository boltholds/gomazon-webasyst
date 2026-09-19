from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import secrets

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from gomazon_webasyst.application.api_execution.services.activity import ApiUserActivityService
from gomazon_webasyst.application.oauth_authorization.composites.authorization import (
    OAuthAuthorizationFlow,
)
from gomazon_webasyst.application.oauth_authorization.composites.revoke_authentication import (
    OAuthRevokeAuthenticationFlow,
)
from gomazon_webasyst.application.oauth_authorization.services.scope import (
    OAuthConsentScopeService,
)
from gomazon_webasyst.application.ports.installed_application_catalog import (
    InstalledApplicationCatalog,
)
from gomazon_webasyst.application.ports.oauth_consent_apps import OAuthConsentAppCatalog
from gomazon_webasyst.application.ports.oauth_redirect_policy import OAuthRedirectPolicy
from gomazon_webasyst.compatibility.webasyst.api.composites.response_renderer import (
    LegacyApiResponseRenderer,
)
from gomazon_webasyst.compatibility.webasyst.api.services.credential_extractor import (
    LegacyApiCredentialExtractionService,
)
from gomazon_webasyst.compatibility.webasyst.api.services.preconditions import (
    LegacyApiTransportPreconditionService,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.cancel import (
    LegacyOAuthCancelService,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.consent_access import (
    LegacyOAuthConsentAccessService,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.controller_format import (
    LegacyOAuthControllerFormatService,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.csrf import (
    LegacyOAuthCsrfService,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.deny import (
    LegacyOAuthDenyService,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.html_renderer import (
    LegacyOAuthHtmlRenderer,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.redirects import (
    LegacyOAuthRedirectService,
    LegacyUnregisteredRedirectPolicy,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.request_validation import (
    LegacyOAuthAuthorizationRequestService,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.revoke_controller import (
    LegacyOAuthRevokeController,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.revoke_target import (
    LegacyRevokeTargetExtractor,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.token_controller import (
    LegacyOAuthControllerRenderer,
    LegacyOAuthTokenController,
    LegacyOAuthTokenRequestService,
)
from gomazon_webasyst.composition.access_control import create_webasyst_rights_evaluator
from gomazon_webasyst.composition.backend_session_bridge import (
    BackendSessionBridgeComponents,
)
from gomazon_webasyst.infrastructure.access_control.sqlalchemy.unit_of_work import (
    SQLAlchemyAccessControlUnitOfWorkFactory,
)
from gomazon_webasyst.infrastructure.api_execution.activity import (
    SQLAlchemyApiUserActivityStore,
)
from gomazon_webasyst.infrastructure.oauth_authorization.app_catalog import (
    InstalledApplicationOAuthConsentAppCatalog,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.consent_application_projector import (
    LegacyOAuthConsentApplicationProjector,
)


def _csrf_generator() -> str:
    return secrets.token_hex(16)


@dataclass(slots=True, frozen=True)
class OAuthAuthorizationComponents:
    authorization_flow: OAuthAuthorizationFlow
    revoke_authentication_flow: OAuthRevokeAuthenticationFlow
    consent_catalog: OAuthConsentAppCatalog
    consent_access_policy: LegacyOAuthConsentAccessService
    redirect_policy: OAuthRedirectPolicy
    authorization_request_service: LegacyOAuthAuthorizationRequestService
    csrf_service: LegacyOAuthCsrfService
    cancel_service: LegacyOAuthCancelService
    deny_service: LegacyOAuthDenyService
    html_renderer: LegacyOAuthHtmlRenderer
    redirect_service: LegacyOAuthRedirectService
    token_request_service: LegacyOAuthTokenRequestService
    token_controller: LegacyOAuthTokenController
    controller_format_service: LegacyOAuthControllerFormatService
    controller_renderer: LegacyOAuthControllerRenderer
    revoke_target_extractor: LegacyRevokeTargetExtractor
    revoke_controller: LegacyOAuthRevokeController
    backend_session_bridge: BackendSessionBridgeComponents
    preconditions: LegacyApiTransportPreconditionService
    credential_extractor: LegacyApiCredentialExtractionService
    framework_response_renderer: LegacyApiResponseRenderer


def create_oauth_authorization_components(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    backend_session_bridge: BackendSessionBridgeComponents,
    issue_authorization_code,
    issue_implicit_api_access_token,
    exchange_authorization_code,
    resolve_api_access_token,
    revoke_api_access_token,
    preconditions: LegacyApiTransportPreconditionService,
    credential_extractor: LegacyApiCredentialExtractionService,
    framework_response_renderer: LegacyApiResponseRenderer,
    consent_catalog: OAuthConsentAppCatalog,
    redirect_policy: OAuthRedirectPolicy,
    csrf_generator: Callable[[], str] = _csrf_generator,
) -> OAuthAuthorizationComponents:
    consent_access = LegacyOAuthConsentAccessService(
        SQLAlchemyAccessControlUnitOfWorkFactory(session_factory),
        create_webasyst_rights_evaluator(),
    )
    scope_service = OAuthConsentScopeService(
        catalog=consent_catalog,
        access=consent_access,
    )
    activity = ApiUserActivityService(
        SQLAlchemyApiUserActivityStore(session_factory),
        clock=datetime.now,
    )
    return OAuthAuthorizationComponents(
        authorization_flow=OAuthAuthorizationFlow(
            scope_service=scope_service,
            issue_authorization_code=issue_authorization_code,
            issue_implicit_api_access_token=issue_implicit_api_access_token,
        ),
        revoke_authentication_flow=OAuthRevokeAuthenticationFlow(
            resolve_access_token=resolve_api_access_token,
            activity_service=activity,
        ),
        consent_catalog=consent_catalog,
        consent_access_policy=consent_access,
        redirect_policy=redirect_policy,
        authorization_request_service=LegacyOAuthAuthorizationRequestService(),
        csrf_service=LegacyOAuthCsrfService(generator=csrf_generator),
        cancel_service=LegacyOAuthCancelService(),
        deny_service=LegacyOAuthDenyService(),
        html_renderer=LegacyOAuthHtmlRenderer(),
        redirect_service=LegacyOAuthRedirectService(),
        token_request_service=LegacyOAuthTokenRequestService(),
        token_controller=LegacyOAuthTokenController(exchange_authorization_code),
        controller_format_service=LegacyOAuthControllerFormatService(),
        controller_renderer=LegacyOAuthControllerRenderer(),
        revoke_target_extractor=LegacyRevokeTargetExtractor(),
        revoke_controller=LegacyOAuthRevokeController(revoke_api_access_token),
        backend_session_bridge=backend_session_bridge,
        preconditions=preconditions,
        credential_extractor=credential_extractor,
        framework_response_renderer=framework_response_renderer,
    )


def create_default_oauth_authorization_components(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    backend_session_bridge: BackendSessionBridgeComponents,
    issue_authorization_code,
    issue_implicit_api_access_token,
    exchange_authorization_code,
    resolve_api_access_token,
    revoke_api_access_token,
    preconditions: LegacyApiTransportPreconditionService,
    credential_extractor: LegacyApiCredentialExtractionService,
    framework_response_renderer: LegacyApiResponseRenderer,
    installed_application_catalog: InstalledApplicationCatalog,
    csrf_generator: Callable[[], str] = _csrf_generator,
) -> OAuthAuthorizationComponents:
    return create_oauth_authorization_components(
        session_factory=session_factory,
        backend_session_bridge=backend_session_bridge,
        issue_authorization_code=issue_authorization_code,
        issue_implicit_api_access_token=issue_implicit_api_access_token,
        exchange_authorization_code=exchange_authorization_code,
        resolve_api_access_token=resolve_api_access_token,
        revoke_api_access_token=revoke_api_access_token,
        preconditions=preconditions,
        credential_extractor=credential_extractor,
        framework_response_renderer=framework_response_renderer,
        consent_catalog=InstalledApplicationOAuthConsentAppCatalog(
            installed_application_catalog,
            LegacyOAuthConsentApplicationProjector(),
        ),
        redirect_policy=LegacyUnregisteredRedirectPolicy(),
        csrf_generator=csrf_generator,
    )
