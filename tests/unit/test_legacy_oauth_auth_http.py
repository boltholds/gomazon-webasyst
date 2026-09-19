from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_credential_values import (
    ApiAccessToken,
    ApiScope,
    AuthorizationCode,
)
from gomazon_webasyst.application.auth_values import SessionId
from gomazon_webasyst.application.oauth_authorization.entities.consent_application import (
    OAuthConsentApplication,
)
from gomazon_webasyst.application.oauth_authorization.vo.authorization import (
    OAuthRedirectMissing,
    OAuthRedirectProvided,
    OAuthRedirectUri,
)
from gomazon_webasyst.application.oauth_authorization.vo.client import (
    OAuthAppDisplayName,
    OAuthAppIconReference,
    OAuthClientName,
)
from gomazon_webasyst.compatibility.webasyst.api.composites.response_renderer import (
    LegacyApiResponseRenderer,
)
from gomazon_webasyst.compatibility.webasyst.api.services.preconditions import (
    LegacyApiTransportPreconditionService,
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
from gomazon_webasyst.compatibility.webasyst.oauth.services.cancel import (
    LegacyOAuthCancelService,
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
from gomazon_webasyst.contracts.auth import AuthenticatedSubject
from gomazon_webasyst.contracts.backend_session_bridge import (
    BackendLogoutCompleted,
    BackendPasswordLoginSucceeded,
    CurrentBackendSubjectResolved,
    CurrentBackendSubjectUnauthenticated,
    IssueSessionCredential,
    KeepSessionCredential,
)
from gomazon_webasyst.contracts.enums import (
    BackendLoginPersistenceStatus,
    CookieSameSite,
    CurrentBackendSubjectReason,
    LogoutStatus,
    PersistentLoginMode,
)
from gomazon_webasyst.contracts.oauth_authorization import (
    OAuthAuthorizationCodeGranted,
    OAuthAuthorizationDenied,
    OAuthConsentRequired,
    OAuthImplicitTokenGranted,
)
from gomazon_webasyst.contracts.persistent_login import (
    ClearPersistentCredential,
    KeepPersistentCredential,
)


SUBJECT = AuthenticatedSubject(id=42, login="admin")
SHOP = OAuthConsentApplication(
    app_id=AppId("shop"),
    display_name=OAuthAppDisplayName("Shop"),
    icon=OAuthAppIconReference("/shop.png"),
)
COOKIE_POLICY = BackendAuthCookiePolicy(
    session_name=CookieName("gomazon_session"),
    persistent_name=CookieName("auth_token"),
    secure=False,
    path="/",
    same_site=CookieSameSite.LAX,
)


class Flow:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def __call__(self, request):
        self.calls.append(request)
        return self.result


class AuthorizationFlow:
    def __init__(self, *, prepare_result=None, decide_result=None):
        self.prepare_result = prepare_result
        self.decide_result = decide_result
        self.prepare_calls = []
        self.decide_calls = []

    async def prepare(self, subject, request):
        self.prepare_calls.append((subject, request))
        return self.prepare_result

    async def decide(self, subject, request, decision):
        self.decide_calls.append((subject, request, decision))
        return self.decide_result


class FailIfCalled:
    def __getattr__(self, name):
        raise AssertionError(f"unexpected access: {name}")

    async def __call__(self, *args, **kwargs):
        raise AssertionError("unexpected call")


class ParseFailIfCalled:
    def parse(self, query):
        raise AssertionError("full oauth request parser must not be called")


class CsrfFailIfCalled:
    def issue(self, cookie):
        raise AssertionError("csrf must not be called")

    def validate(self, cookie, form):
        raise AssertionError("csrf must not be called")


def unauthenticated():
    return CurrentBackendSubjectUnauthenticated(
        reason=CurrentBackendSubjectReason.NO_CREDENTIAL,
        session_disposition=KeepSessionCredential(),
        persistent_disposition=KeepPersistentCredential(),
    )


def authenticated():
    return CurrentBackendSubjectResolved(
        subject=SUBJECT,
        session_disposition=KeepSessionCredential(),
        persistent_disposition=KeepPersistentCredential(),
    )


def bridge(*, current_result, login_result=None, logout_result=None):
    return SimpleNamespace(
        current_subject_flow=Flow(current_result),
        password_login_flow=Flow(login_result) if login_result is not None else FailIfCalled(),
        logout_flow=Flow(logout_result) if logout_result is not None else FailIfCalled(),
        credential_extractor=BackendAuthCredentialExtractionService(),
        cookie_mutation_service=BackendAuthCookieMutationService(
            clock=lambda: datetime(2026, 9, 19, tzinfo=timezone.utc)
        ),
        cookie_policy=COOKIE_POLICY,
        persistent_login_mode=PersistentLoginMode.ENABLED,
    )


def components(
    *,
    current_result=None,
    login_result=None,
    logout_result=None,
    prepare_result=None,
    decide_result=None,
    request_service=None,
    csrf_service=None,
    preconditions=None,
):
    backend = bridge(
        current_result=current_result or unauthenticated(),
        login_result=login_result,
        logout_result=logout_result,
    )
    return SimpleNamespace(
        backend_session_bridge=backend,
        authorization_flow=AuthorizationFlow(
            prepare_result=prepare_result,
            decide_result=decide_result,
        ),
        authorization_request_service=(
            request_service or LegacyOAuthAuthorizationRequestService()
        ),
        csrf_service=csrf_service or LegacyOAuthCsrfService(generator=lambda: "csrf-token"),
        cancel_service=LegacyOAuthCancelService(),
        deny_service=LegacyOAuthDenyService(),
        redirect_service=LegacyOAuthRedirectService(),
        redirect_policy=LegacyUnregisteredRedirectPolicy(),
        html_renderer=LegacyOAuthHtmlRenderer(),
        preconditions=preconditions
        or LegacyApiTransportPreconditionService(
            api_enabled=True,
            disable_message="",
            force_https=False,
        ),
        framework_response_renderer=LegacyApiResponseRenderer(),
    )


def client_for(parts):
    from gomazon_webasyst.presentation.http.legacy_oauth import (
        create_legacy_oauth_router,
    )

    app = FastAPI()
    app.include_router(create_legacy_oauth_router(parts))
    return TestClient(app)


def auth_url(response_type="code", *, redirect=True):
    base = (
        "/api.php/auth?client_id=client&client_name=Demo"
        f"&response_type={response_type}&scope=shop"
    )
    if redirect:
        base += "&redirect_uri=https://client.test/cb"
    return base


def test_cancel_runs_before_current_subject_csrf_and_full_validation() -> None:
    parts = components(
        current_result=unauthenticated(),
        request_service=ParseFailIfCalled(),
        csrf_service=CsrfFailIfCalled(),
    )
    parts.backend_session_bridge.current_subject_flow = FailIfCalled()
    response = client_for(parts).post(
        "/api.php/auth?response_type=code&redirect_uri=https://client.test/cb"
        "&client_name=Demo",
        data={"cancel": "1", "_csrf": "wrong"},
        cookies={"gomazon_session": "stale"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == "https://client.test/cb?error=access_denied"


def test_unauthenticated_get_renders_login_before_full_oauth_validation() -> None:
    parts = components(
        request_service=ParseFailIfCalled(),
        current_result=unauthenticated(),
    )
    response = client_for(parts).get("/api.php/auth?client_name=Demo")
    assert response.status_code == 200
    assert "<form" in response.text
    assert "Demo" in response.text
    assert "_csrf" in response.cookies


def test_successful_backend_login_sets_session_and_redirects_to_same_oauth_url() -> None:
    login_result = BackendPasswordLoginSucceeded(
        subject=SUBJECT,
        session_disposition=IssueSessionCredential(session_id=SessionId("sess-new")),
        persistent_disposition=KeepPersistentCredential(),
        persistence_status=BackendLoginPersistenceStatus.SESSION_ONLY,
    )
    parts = components(
        current_result=unauthenticated(),
        login_result=login_result,
        request_service=ParseFailIfCalled(),
    )
    url = auth_url()
    response = client_for(parts).post(
        url,
        data={
            "_csrf": "csrf-token",
            "identifier": "admin",
            "password": "secret",
            "login": "1",
        },
        cookies={"_csrf": "csrf-token"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == f"http://testserver{url}"
    assert response.cookies["gomazon_session"] == "sess-new"


def test_authenticated_get_renders_filtered_consent() -> None:
    result = OAuthConsentRequired(
        client_name=OAuthClientName("Demo"),
        effective_scope=ApiScope((AppId("shop"),)),
        applications=(SHOP,),
    )
    parts = components(
        current_result=authenticated(),
        prepare_result=result,
    )
    response = client_for(parts).get(auth_url())
    assert response.status_code == 200
    assert "Shop" in response.text
    assert "Demo" in response.text
    assert "_csrf" in response.cookies


def test_code_approval_redirects_using_legacy_query_semantics() -> None:
    result = OAuthAuthorizationCodeGranted(
        code=AuthorizationCode("c" * 32),
        redirect_target=OAuthRedirectProvided(
            OAuthRedirectUri("https://client.test/cb?existing=1")
        ),
    )
    parts = components(
        current_result=authenticated(),
        decide_result=result,
    )
    response = client_for(parts).post(
        auth_url(redirect=False)
        + "&redirect_uri=https://client.test/cb?existing=1",
        data={"_csrf": "same", "approve": "1"},
        cookies={"_csrf": "same"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == (
        "https://client.test/cb?existing=1&code=" + "c" * 32
    )


def test_code_approval_without_redirect_renders_code_page() -> None:
    result = OAuthAuthorizationCodeGranted(
        code=AuthorizationCode("c" * 32),
        redirect_target=OAuthRedirectMissing(),
    )
    parts = components(
        current_result=authenticated(),
        decide_result=result,
    )
    response = client_for(parts).post(
        auth_url(redirect=False),
        data={"_csrf": "same", "approve": "1"},
        cookies={"_csrf": "same"},
    )
    assert response.status_code == 200
    assert "c" * 32 in response.text


def test_implicit_token_approval_uses_fragment_redirect() -> None:
    result = OAuthImplicitTokenGranted(
        access_token=ApiAccessToken("a" * 32),
        redirect_target=OAuthRedirectProvided(
            OAuthRedirectUri("https://client.test/cb")
        ),
    )
    parts = components(
        current_result=authenticated(),
        decide_result=result,
    )
    response = client_for(parts).post(
        auth_url("token"),
        data={"_csrf": "same", "approve": "1"},
        cookies={"_csrf": "same"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == (
        "https://client.test/cb#access_token=" + "a" * 32
    )


def test_authenticated_code_deny_without_redirect_renders_html_error() -> None:
    result = OAuthAuthorizationDenied(
        response_type=__import__(
            "gomazon_webasyst.contracts.enums",
            fromlist=["OAuthResponseType"],
        ).OAuthResponseType.CODE,
        redirect_target=OAuthRedirectMissing(),
        client_name=OAuthClientName("Demo"),
    )
    parts = components(
        current_result=authenticated(),
        decide_result=result,
    )
    response = client_for(parts).post(
        auth_url(redirect=False),
        data={"_csrf": "same", "deny": "1"},
        cookies={"_csrf": "same"},
    )
    assert response.status_code == 200
    assert "access_denied" in response.text


def test_authenticated_logout_clears_auth_cookies_and_redirects_same_url() -> None:
    logout_result = BackendLogoutCompleted(
        session_status=LogoutStatus.REVOKED,
        session_disposition=__import__(
            "gomazon_webasyst.contracts.backend_session_bridge",
            fromlist=["ClearSessionCredential"],
        ).ClearSessionCredential(),
        persistent_disposition=ClearPersistentCredential(),
    )
    parts = components(
        current_result=authenticated(),
        logout_result=logout_result,
        prepare_result=OAuthConsentRequired(
            client_name=OAuthClientName("Demo"),
            effective_scope=ApiScope((AppId("shop"),)),
            applications=(SHOP,),
        ),
    )
    url = auth_url()
    response = client_for(parts).post(
        url,
        data={"_csrf": "same", "logout": "1"},
        cookies={
            "_csrf": "same",
            "gomazon_session": "sess",
            "auth_token": "persistent",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == f"http://testserver{url}"
    assert response.cookies.get("gomazon_session") is None
    assert response.cookies.get("auth_token") is None


def test_api_disabled_and_https_preconditions_run_before_cancel() -> None:
    disabled = components(
        current_result=unauthenticated(),
        request_service=ParseFailIfCalled(),
        csrf_service=CsrfFailIfCalled(),
        preconditions=LegacyApiTransportPreconditionService(
            api_enabled=False,
            disable_message="disabled",
            force_https=False,
        ),
    )
    disabled.backend_session_bridge.current_subject_flow = FailIfCalled()
    response = client_for(disabled).post(
        "/api.php/auth",
        data={"cancel": "1"},
        follow_redirects=False,
    )
    assert response.status_code == 404
    assert response.json()["error"] == "disabled"

    https = components(
        current_result=unauthenticated(),
        request_service=ParseFailIfCalled(),
        csrf_service=CsrfFailIfCalled(),
        preconditions=LegacyApiTransportPreconditionService(
            api_enabled=True,
            disable_message="",
            force_https=True,
        ),
    )
    https.backend_session_bridge.current_subject_flow = FailIfCalled()
    response = client_for(https).post(
        "/api.php/auth",
        data={"cancel": "1"},
        follow_redirects=False,
    )
    assert response.status_code == 301
    assert response.headers["location"].startswith("https://")
