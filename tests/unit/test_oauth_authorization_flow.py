from datetime import datetime, timezone
from importlib import import_module

import pytest

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_credential_values import (
    ApiAccessToken,
    ApiClientId,
    ApiScope,
    AuthorizationCode,
)
from gomazon_webasyst.application.oauth_authorization.composites.requests import (
    OAuthAuthorizationRequest,
)
from gomazon_webasyst.application.oauth_authorization.entities.consent_application import (
    OAuthConsentApplication,
)
from gomazon_webasyst.application.oauth_authorization.services.scope import (
    OAuthEffectiveScopeEmpty,
    OAuthEffectiveScopeResolved,
)
from gomazon_webasyst.application.oauth_authorization.vo.authorization import (
    OAuthRedirectMissing,
    OAuthRequestedScope,
)
from gomazon_webasyst.application.oauth_authorization.vo.client import (
    OAuthAppDisplayName,
    OAuthAppIconReference,
    OAuthClientName,
)
from gomazon_webasyst.contracts.api_credentials import (
    ApiAccessTokenIssueRejected,
    ApiAccessTokenIssued,
    AuthorizationCodeIssueRejected,
    AuthorizationCodeIssued,
    StoredAuthorizationCode,
)
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.enums import (
    ApiAccessTokenIssueRejectReason,
    AuthorizationCodeIssueRejectReason,
    OAuthConsentDecision,
    OAuthResponseType,
)


SUBJECT = AuthenticatedSubject(id=42, login="admin")
CLIENT = ApiClientId("client")
SHOP = AppId("shop")
CRM = AppId("crm")
REQUESTED = OAuthRequestedScope((SHOP, CRM))
EFFECTIVE_SCOPE = ApiScope((SHOP,))
SHOP_APP = OAuthConsentApplication(
    app_id=SHOP,
    display_name=OAuthAppDisplayName("Shop"),
    icon=OAuthAppIconReference("/shop.png"),
)
EFFECTIVE = OAuthEffectiveScopeResolved(
    scope=EFFECTIVE_SCOPE,
    applications=(SHOP_APP,),
)
CODE = AuthorizationCode("c" * 32)
TOKEN = ApiAccessToken("a" * 32)


def _flow_class():
    try:
        return import_module(
            "gomazon_webasyst.application.oauth_authorization.composites.authorization"
        ).OAuthAuthorizationFlow
    except (ModuleNotFoundError, AttributeError) as error:
        pytest.fail(f"oauth authorization flow missing: {error}")


def request(response_type: OAuthResponseType):
    return OAuthAuthorizationRequest(
        client_id=CLIENT,
        client_name=OAuthClientName("Client"),
        response_type=response_type,
        requested_scope=REQUESTED,
        redirect_target=OAuthRedirectMissing(),
    )


class ScopeService:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def filter(self, subject, requested):
        self.calls.append((subject, requested))
        return self.result


class CodeIssuer:
    def __init__(self, result=None):
        self.result = result or AuthorizationCodeIssued(
            record=StoredAuthorizationCode(
                code=CODE,
                contact_id=42,
                client_id=CLIENT,
                scope=EFFECTIVE_SCOPE,
                expires_at=datetime(2026, 9, 19, 12, 3, tzinfo=timezone.utc),
            )
        )
        self.calls = []

    async def __call__(self, subject, client_id, scope):
        self.calls.append((subject, client_id, scope))
        return self.result


class TokenIssuer:
    def __init__(self, result=None):
        self.result = result or ApiAccessTokenIssued(
            access_token=TOKEN,
            scope=EFFECTIVE_SCOPE,
        )
        self.calls = []

    async def __call__(self, subject, client_id, scope):
        self.calls.append((subject, client_id, scope))
        return self.result


class FailIfCalled:
    async def __call__(self, *args):
        raise AssertionError("issuer must not be called")


@pytest.mark.asyncio
async def test_prepare_returns_consent_with_effective_scope_and_apps() -> None:
    contracts = import_module("gomazon_webasyst.contracts.oauth_authorization")
    flow = _flow_class()(
        scope_service=ScopeService(EFFECTIVE),
        issue_authorization_code=FailIfCalled(),
        issue_implicit_api_access_token=FailIfCalled(),
    )

    result = await flow.prepare(SUBJECT, request(OAuthResponseType.CODE))

    assert isinstance(result, contracts.OAuthConsentRequired)
    assert result.effective_scope == EFFECTIVE_SCOPE
    assert result.applications == (SHOP_APP,)


@pytest.mark.asyncio
async def test_prepare_empty_scope_short_circuits() -> None:
    contracts = import_module("gomazon_webasyst.contracts.oauth_authorization")
    flow = _flow_class()(
        scope_service=ScopeService(OAuthEffectiveScopeEmpty()),
        issue_authorization_code=FailIfCalled(),
        issue_implicit_api_access_token=FailIfCalled(),
    )
    result = await flow.prepare(SUBJECT, request(OAuthResponseType.CODE))
    assert isinstance(result, contracts.OAuthAuthorizationInvalidScope)


@pytest.mark.asyncio
async def test_code_approval_uses_effective_scope_only() -> None:
    contracts = import_module("gomazon_webasyst.contracts.oauth_authorization")
    issuer = CodeIssuer()
    flow = _flow_class()(
        scope_service=ScopeService(EFFECTIVE),
        issue_authorization_code=issuer,
        issue_implicit_api_access_token=FailIfCalled(),
    )

    result = await flow.decide(
        SUBJECT,
        request(OAuthResponseType.CODE),
        OAuthConsentDecision.APPROVE,
    )

    assert isinstance(result, contracts.OAuthAuthorizationCodeGranted)
    assert result.code == CODE
    assert issuer.calls == [(SUBJECT, CLIENT, EFFECTIVE_SCOPE)]


@pytest.mark.asyncio
async def test_implicit_approval_uses_effective_scope_only() -> None:
    contracts = import_module("gomazon_webasyst.contracts.oauth_authorization")
    issuer = TokenIssuer()
    flow = _flow_class()(
        scope_service=ScopeService(EFFECTIVE),
        issue_authorization_code=FailIfCalled(),
        issue_implicit_api_access_token=issuer,
    )

    result = await flow.decide(
        SUBJECT,
        request(OAuthResponseType.TOKEN),
        OAuthConsentDecision.APPROVE,
    )

    assert isinstance(result, contracts.OAuthImplicitTokenGranted)
    assert result.access_token == TOKEN
    assert issuer.calls == [(SUBJECT, CLIENT, EFFECTIVE_SCOPE)]


@pytest.mark.asyncio
async def test_authenticated_deny_invokes_no_issuer() -> None:
    contracts = import_module("gomazon_webasyst.contracts.oauth_authorization")
    flow = _flow_class()(
        scope_service=ScopeService(EFFECTIVE),
        issue_authorization_code=FailIfCalled(),
        issue_implicit_api_access_token=FailIfCalled(),
    )
    req = request(OAuthResponseType.CODE)

    result = await flow.decide(
        SUBJECT,
        req,
        OAuthConsentDecision.DENY,
    )

    assert isinstance(result, contracts.OAuthAuthorizationDenied)
    assert result.response_type is OAuthResponseType.CODE
    assert result.redirect_target == req.redirect_target
    assert result.client_name == req.client_name


@pytest.mark.asyncio
async def test_empty_effective_scope_beats_deny_or_approval() -> None:
    contracts = import_module("gomazon_webasyst.contracts.oauth_authorization")
    flow = _flow_class()(
        scope_service=ScopeService(OAuthEffectiveScopeEmpty()),
        issue_authorization_code=FailIfCalled(),
        issue_implicit_api_access_token=FailIfCalled(),
    )
    result = await flow.decide(
        SUBJECT,
        request(OAuthResponseType.CODE),
        OAuthConsentDecision.DENY,
    )
    assert isinstance(result, contracts.OAuthAuthorizationInvalidScope)


@pytest.mark.asyncio
async def test_code_issue_rejection_maps_to_grant_unavailable() -> None:
    contracts = import_module("gomazon_webasyst.contracts.oauth_authorization")
    flow = _flow_class()(
        scope_service=ScopeService(EFFECTIVE),
        issue_authorization_code=CodeIssuer(
            AuthorizationCodeIssueRejected(
                reason=AuthorizationCodeIssueRejectReason.COLLISION
            )
        ),
        issue_implicit_api_access_token=FailIfCalled(),
    )
    result = await flow.decide(
        SUBJECT,
        request(OAuthResponseType.CODE),
        OAuthConsentDecision.APPROVE,
    )
    assert isinstance(result, contracts.OAuthAuthorizationGrantUnavailable)


@pytest.mark.asyncio
async def test_token_issue_rejection_maps_to_grant_unavailable() -> None:
    contracts = import_module("gomazon_webasyst.contracts.oauth_authorization")
    flow = _flow_class()(
        scope_service=ScopeService(EFFECTIVE),
        issue_authorization_code=FailIfCalled(),
        issue_implicit_api_access_token=TokenIssuer(
            ApiAccessTokenIssueRejected(
                reason=ApiAccessTokenIssueRejectReason.CONCURRENT_STATE_CHANGED
            )
        ),
    )
    result = await flow.decide(
        SUBJECT,
        request(OAuthResponseType.TOKEN),
        OAuthConsentDecision.APPROVE,
    )
    assert isinstance(result, contracts.OAuthAuthorizationGrantUnavailable)
