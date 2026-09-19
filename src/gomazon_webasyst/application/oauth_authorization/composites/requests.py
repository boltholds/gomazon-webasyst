from dataclasses import dataclass

from gomazon_webasyst.application.api_credential_values import ApiClientId
from gomazon_webasyst.application.oauth_authorization.vo.authorization import (
    OAuthRedirectTarget,
    OAuthRequestedScope,
)
from gomazon_webasyst.application.oauth_authorization.vo.client import OAuthClientName
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.enums import OAuthConsentDecision, OAuthResponseType


@dataclass(slots=True, frozen=True)
class OAuthAuthorizationRequest:
    client_id: ApiClientId
    client_name: OAuthClientName
    response_type: OAuthResponseType
    requested_scope: OAuthRequestedScope
    redirect_target: OAuthRedirectTarget


@dataclass(slots=True, frozen=True)
class OAuthAuthenticatedDecisionRequest:
    subject: AuthenticatedSubject
    authorization_request: OAuthAuthorizationRequest
    decision: OAuthConsentDecision
