import json
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from gomazon_webasyst.application.api_credential_values import (
    ApiAccessToken,
    ApiClientId,
    ApiScope,
)
from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.oauth_authorization.composites.revoke_authentication import (
    OAuthRevokeAuthenticated,
    OAuthRevokeAuthenticationRejected,
)
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
from gomazon_webasyst.compatibility.webasyst.oauth.services.controller_format import (
    LegacyOAuthControllerFormatService,
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
from gomazon_webasyst.contracts.api_credentials import (
    ApiAccessTokenResolved,
    AuthorizationCodeExchanged,
)
from gomazon_webasyst.contracts.enums import (
    ApiAccessTokenResolveRejectReason,
)
from gomazon_webasyst.presentation.http.legacy_oauth import (
    create_legacy_oauth_router,
)


TOKEN_A = ApiAccessToken("a" * 32)
TOKEN_B = ApiAccessToken("b" * 32)


class Exchange:
    def __init__(self):
        self.calls = []

    async def __call__(self, code, client_id):
        self.calls.append((code, client_id))
        return AuthorizationCodeExchanged(
            access_token=TOKEN_A,
            scope=ApiScope((AppId("shop"),)),
        )


class RevokeAuth:
    def __init__(self, *, rejected=False):
        self.calls = []
        self.rejected = rejected

    async def authenticate(self, token):
        self.calls.append(token)
        if self.rejected:
            return OAuthRevokeAuthenticationRejected(
                ApiAccessTokenResolveRejectReason.MISSING
            )
        return OAuthRevokeAuthenticated(contact_id=42, token=token)


class Revoker:
    def __init__(self):
        self.calls = []

    async def __call__(self, token):
        from gomazon_webasyst.contracts.api_credentials import ApiAccessTokenRevoked
        self.calls.append(token)
        return ApiAccessTokenRevoked(access_token=token)


def parts(*, rejected=False):
    exchange = Exchange()
    auth = RevokeAuth(rejected=rejected)
    revoker = Revoker()
    return SimpleNamespace(
        preconditions=LegacyApiTransportPreconditionService(
            api_enabled=True,
            disable_message="",
            force_https=False,
        ),
        credential_extractor=LegacyApiCredentialExtractionService(),
        framework_response_renderer=LegacyApiResponseRenderer(),
        controller_format_service=LegacyOAuthControllerFormatService(),
        token_request_service=LegacyOAuthTokenRequestService(),
        token_controller=LegacyOAuthTokenController(exchange),
        controller_renderer=LegacyOAuthControllerRenderer(),
        revoke_authentication_flow=auth,
        revoke_target_extractor=LegacyRevokeTargetExtractor(),
        revoke_controller=LegacyOAuthRevokeController(revoker),
        cancel_service=LegacyOAuthCancelService(),
        exchange=exchange,
        revoke_auth=auth,
        revoker=revoker,
    )


def client_for(components):
    app = FastAPI()
    app.include_router(create_legacy_oauth_router(components))
    return TestClient(app)


def token_form():
    return {
        "code": "c" * 32,
        "client_id": "client",
        "grant_type": "authorization_code",
    }


def test_token_success_and_xml_controller_responses_are_http_200_without_jsonp() -> None:
    p = parts()
    client = client_for(p)

    response = client.post("/api.php/token?callback=cb", data=token_form())
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"access_token": TOKEN_A.value}
    assert not response.text.startswith("cb(")

    xml = client.post("/api.php/token?format=xml&callback=cb", data=token_form())
    assert xml.status_code == 200
    assert xml.headers["content-type"].startswith("application/xml")
    assert f"<access_token>{TOKEN_A.value}</access_token>" in xml.text
    assert "cb(" not in xml.text


def test_token_protocol_fields_are_post_only_and_get_returns_controller_error_not_405() -> None:
    response = client_for(parts()).get(
        "/api.php/token",
        params={
            "code": "c" * 32,
            "client_id": "client",
            "grant_type": "authorization_code",
        },
    )
    assert response.status_code == 200
    assert response.json()["error"] == "invalid_request"
    assert "code" in response.json()["error_description"]


def test_token_invalid_format_is_json_http_200_and_callback_is_ignored() -> None:
    response = client_for(parts()).post(
        "/api.php/token?format=yaml&callback=cb",
        data=token_form(),
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["error"] == "invalid_request"
    assert not response.text.startswith("cb(")


def test_revoke_request_token_has_precedence_over_bearer_and_targets_same_token() -> None:
    p = parts()
    response = client_for(p).post(
        "/api.php/revoke",
        data={"access_token": TOKEN_A.value},
        headers={"Authorization": f"Bearer {TOKEN_B.value}"},
    )
    assert response.status_code == 200
    assert response.json() == {"access_token": TOKEN_A.value}
    assert p.revoke_auth.calls == [TOKEN_A]
    assert p.revoker.calls == [TOKEN_A]


def test_revoke_header_only_authenticates_but_controller_target_is_missing_noop() -> None:
    p = parts()
    response = client_for(p).get(
        "/api.php/revoke?callback=cb",
        headers={"Authorization": f"Bearer {TOKEN_B.value}"},
    )
    assert response.status_code == 200
    assert response.json() == {"access_token": ""}
    assert not response.text.startswith("cb(")
    assert p.revoke_auth.calls == [TOKEN_B]
    assert p.revoker.calls == []


def test_revoke_missing_token_uses_framework_error_and_jsonp_semantics() -> None:
    response = client_for(parts()).get("/api.php/revoke")
    assert response.status_code == 400
    assert response.json()["error"] == "token_required"

    jsonp = client_for(parts()).get("/api.php/revoke?callback=cb")
    assert jsonp.status_code == 200
    assert jsonp.headers["content-type"].startswith("text/javascript")
    assert jsonp.text.startswith("cb(")
    assert "token_required" in jsonp.text


def test_revoke_invalid_auth_precedes_controller_format_validation() -> None:
    p = parts(rejected=True)
    response = client_for(p).get(
        "/api.php/revoke?format=yaml",
        headers={"Authorization": f"Bearer {TOKEN_A.value}"},
    )
    assert response.status_code == 401
    assert response.json()["error"] == "invalid_token"
    assert p.revoke_auth.calls == [TOKEN_A]


def test_revoke_controller_invalid_format_is_http_200_json_without_jsonp() -> None:
    p = parts()
    response = client_for(p).get(
        "/api.php/revoke?format=yaml&callback=cb",
        headers={"Authorization": f"Bearer {TOKEN_A.value}"},
    )
    assert response.status_code == 200
    assert response.json()["error"] == "invalid_request"
    assert not response.text.startswith("cb(")
