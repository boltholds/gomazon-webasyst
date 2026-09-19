from gomazon_webasyst.application.oauth_authorization.composites.requests import (
    OAuthAuthorizationRequest,
)
from gomazon_webasyst.application.oauth_authorization.services.scope import (
    OAuthConsentScopeService,
    OAuthEffectiveScopeEmpty,
    OAuthEffectiveScopeResolved,
)
from gomazon_webasyst.contracts.api_credentials import (
    ApiAccessTokenIssueRejected,
    ApiAccessTokenIssued,
    AuthorizationCodeIssueRejected,
    AuthorizationCodeIssued,
)
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.enums import OAuthConsentDecision, OAuthResponseType
from gomazon_webasyst.contracts.oauth_authorization import (
    OAuthAuthorizationCodeGranted,
    OAuthAuthorizationDenied,
    OAuthAuthorizationGrantUnavailable,
    OAuthAuthorizationInvalidScope,
    OAuthAuthorizationResult,
    OAuthConsentRequired,
    OAuthImplicitTokenGranted,
)


class OAuthAuthorizationFlow:
    def __init__(
        self,
        *,
        scope_service: OAuthConsentScopeService,
        issue_authorization_code,
        issue_implicit_api_access_token,
    ) -> None:
        self._scope_service = scope_service
        self._issue_authorization_code = issue_authorization_code
        self._issue_implicit_api_access_token = issue_implicit_api_access_token

    async def prepare(
        self,
        subject: AuthenticatedSubject,
        authorization_request: OAuthAuthorizationRequest,
    ) -> OAuthAuthorizationResult:
        effective = await self._scope_service.filter(
            subject,
            authorization_request.requested_scope,
        )
        if isinstance(effective, OAuthEffectiveScopeEmpty):
            return OAuthAuthorizationInvalidScope()
        if not isinstance(effective, OAuthEffectiveScopeResolved):
            raise AssertionError("unsupported oauth effective scope result")

        return OAuthConsentRequired(
            client_name=authorization_request.client_name,
            effective_scope=effective.scope,
            applications=effective.applications,
        )

    async def decide(
        self,
        subject: AuthenticatedSubject,
        authorization_request: OAuthAuthorizationRequest,
        decision: OAuthConsentDecision,
    ) -> OAuthAuthorizationResult:
        effective = await self._scope_service.filter(
            subject,
            authorization_request.requested_scope,
        )
        if isinstance(effective, OAuthEffectiveScopeEmpty):
            return OAuthAuthorizationInvalidScope()
        if not isinstance(effective, OAuthEffectiveScopeResolved):
            raise AssertionError("unsupported oauth effective scope result")

        if decision is OAuthConsentDecision.DENY:
            return OAuthAuthorizationDenied(
                response_type=authorization_request.response_type,
                redirect_target=authorization_request.redirect_target,
                client_name=authorization_request.client_name,
            )
        if decision is not OAuthConsentDecision.APPROVE:
            raise AssertionError("unsupported oauth consent decision")

        if authorization_request.response_type is OAuthResponseType.CODE:
            issued = await self._issue_authorization_code(
                subject,
                authorization_request.client_id,
                effective.scope,
            )
            if isinstance(issued, AuthorizationCodeIssued):
                return OAuthAuthorizationCodeGranted(
                    code=issued.record.code,
                    redirect_target=authorization_request.redirect_target,
                )
            if isinstance(issued, AuthorizationCodeIssueRejected):
                return OAuthAuthorizationGrantUnavailable()
            raise AssertionError("unsupported authorization code issue result")

        if authorization_request.response_type is OAuthResponseType.TOKEN:
            issued = await self._issue_implicit_api_access_token(
                subject,
                authorization_request.client_id,
                effective.scope,
            )
            if isinstance(issued, ApiAccessTokenIssued):
                return OAuthImplicitTokenGranted(
                    access_token=issued.access_token,
                    redirect_target=authorization_request.redirect_target,
                )
            if isinstance(issued, ApiAccessTokenIssueRejected):
                return OAuthAuthorizationGrantUnavailable()
            raise AssertionError("unsupported api access token issue result")

        raise AssertionError("unsupported oauth response type")
