from importlib import import_module
from types import SimpleNamespace

import pytest

from gomazon_webasyst.compatibility.webasyst.api.composites.response_renderer import (
    LegacyApiResponseRenderer,
)
from gomazon_webasyst.compatibility.webasyst.api.services.credential_extractor import (
    LegacyApiCredentialExtractionService,
)
from gomazon_webasyst.compatibility.webasyst.api.services.preconditions import (
    LegacyApiTransportPreconditionService,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.redirects import (
    LegacyUnregisteredRedirectPolicy,
)
from gomazon_webasyst.infrastructure.oauth_authorization.app_catalog import (
    InMemoryOAuthConsentAppCatalog,
)


def _module():
    try:
        return import_module("gomazon_webasyst.composition.oauth_authorization")
    except ModuleNotFoundError as error:
        pytest.fail(f"oauth authorization composition missing: {error}")


def dependencies():
    return {
        "session_factory": object(),
        "backend_session_bridge": object(),
        "issue_authorization_code": object(),
        "issue_implicit_api_access_token": object(),
        "exchange_authorization_code": object(),
        "resolve_api_access_token": object(),
        "revoke_api_access_token": object(),
        "preconditions": LegacyApiTransportPreconditionService(
            api_enabled=True,
            disable_message="",
            force_https=False,
        ),
        "credential_extractor": LegacyApiCredentialExtractionService(),
        "framework_response_renderer": LegacyApiResponseRenderer(),
        "consent_catalog": InMemoryOAuthConsentAppCatalog(()),
        "redirect_policy": LegacyUnregisteredRedirectPolicy(),
    }


def test_composition_reuses_existing_auth_and_credential_dependencies() -> None:
    m = _module()
    deps = dependencies()
    parts = m.create_oauth_authorization_components(
        **deps,
        csrf_generator=lambda: "csrf",
    )

    assert parts.backend_session_bridge is deps["backend_session_bridge"]
    assert (
        parts.authorization_flow._issue_authorization_code
        is deps["issue_authorization_code"]
    )
    assert (
        parts.authorization_flow._issue_implicit_api_access_token
        is deps["issue_implicit_api_access_token"]
    )
    assert (
        parts.revoke_authentication_flow._resolve_access_token
        is deps["resolve_api_access_token"]
    )
    assert parts.token_controller._exchange_authorization_code is deps[
        "exchange_authorization_code"
    ]
    assert parts.revoke_controller._revoke_api_access_token is deps[
        "revoke_api_access_token"
    ]
    assert parts.preconditions is deps["preconditions"]
    assert parts.credential_extractor is deps["credential_extractor"]
    assert (
        parts.framework_response_renderer
        is deps["framework_response_renderer"]
    )
    assert parts.token_request_service is not None
    assert parts.redirect_service is not None


def test_default_composition_uses_empty_catalog_and_legacy_redirect_policy() -> None:
    m = _module()
    deps = dependencies()
    deps.pop("consent_catalog")
    deps.pop("redirect_policy")
    parts = m.create_default_oauth_authorization_components(
        **deps,
        csrf_generator=lambda: "csrf",
    )

    missing = parts.consent_catalog.resolve(
        __import__(
            "gomazon_webasyst.application.access_values",
            fromlist=["AppId"],
        ).AppId("shop")
    )
    assert type(missing).__name__ == "OAuthConsentApplicationMissing"
    assert isinstance(parts.redirect_policy, LegacyUnregisteredRedirectPolicy)
