from datetime import datetime, timedelta
from importlib import import_module

import pytest

from gomazon_webasyst.application.auth_values import SessionId
from gomazon_webasyst.application.backend_session_bridge.vo.credentials import (
    PersistentCredentialMissing,
    PersistentCredentialProvided,
    SessionCredentialMalformed,
    SessionCredentialMissing,
    SessionCredentialProvided,
)
from gomazon_webasyst.application.persistent_values import (
    PersistentCredential,
    PersistentCredentialLifetime,
)
from gomazon_webasyst.contracts.backend_session_bridge import (
    ClearSessionCredential,
    IssueSessionCredential,
    KeepSessionCredential,
)
from gomazon_webasyst.contracts.persistent_login import (
    ClearPersistentCredential,
    KeepPersistentCredential,
    RefreshPersistentCredential,
)


NOW = datetime(2026, 9, 19, 12, 0, 0)


def _modules():
    try:
        cookies = import_module(
            "gomazon_webasyst.compatibility.webasyst.auth_http.vo.cookies"
        )
        requests = import_module(
            "gomazon_webasyst.compatibility.webasyst.auth_http.composites.request"
        )
        mutations = import_module(
            "gomazon_webasyst.compatibility.webasyst.auth_http.composites.cookies"
        )
        extraction = import_module(
            "gomazon_webasyst.compatibility.webasyst.auth_http.services.credentials"
        )
        planner = import_module(
            "gomazon_webasyst.compatibility.webasyst.auth_http.services.cookie_mutations"
        )
        return cookies, requests, mutations, extraction, planner
    except ModuleNotFoundError as error:
        pytest.fail(f"auth http compatibility package missing: {error}")


def policy(*, secure=False):
    cookies, _, _, _, _ = _modules()
    return cookies.BackendAuthCookiePolicy(
        session_name=cookies.CookieName("gomazon_session"),
        persistent_name=cookies.CookieName("auth_token"),
        secure=secure,
        path="/",
        same_site=cookies.CookieSameSite.LAX,
    )


@pytest.mark.parametrize("raw", ["", "0"])
def test_php_falsy_auth_token_is_not_sent_to_persistent_strategy(raw: str) -> None:
    _, _, _, extraction, _ = _modules()
    state = extraction.BackendAuthCredentialExtractionService().extract(
        cookies={"auth_token": raw},
        user_agent="pytest",
        policy=policy(),
    )
    assert isinstance(state.persistent_credential, PersistentCredentialMissing)


def test_empty_session_cookie_is_malformed_not_missing() -> None:
    _, _, _, extraction, _ = _modules()
    state = extraction.BackendAuthCredentialExtractionService().extract(
        cookies={"gomazon_session": ""},
        user_agent="pytest",
        policy=policy(),
    )
    assert isinstance(state.session_credential, SessionCredentialMalformed)


def test_session_zero_is_valid_opaque_session_and_user_agent_is_preserved() -> None:
    _, _, _, extraction, _ = _modules()
    state = extraction.BackendAuthCredentialExtractionService().extract(
        cookies={"gomazon_session": "0", "auth_token": "credential"},
        user_agent="Browser/1.0",
        policy=policy(),
    )
    assert state.session_credential == SessionCredentialProvided(SessionId("0"))
    assert state.persistent_credential == PersistentCredentialProvided(
        PersistentCredential("credential")
    )
    assert state.session_metadata.user_agent == "Browser/1.0"


def test_custom_cookie_names_are_respected() -> None:
    cookies_mod, _, _, extraction, _ = _modules()
    custom = cookies_mod.BackendAuthCookiePolicy(
        session_name=cookies_mod.CookieName("custom_session"),
        persistent_name=cookies_mod.CookieName("custom_persistent"),
        secure=False,
        path="/",
        same_site=cookies_mod.CookieSameSite.LAX,
    )
    state = extraction.BackendAuthCredentialExtractionService().extract(
        cookies={
            "gomazon_session": "wrong",
            "auth_token": "wrong",
            "custom_session": "sess",
            "custom_persistent": "persistent",
        },
        user_agent="",
        policy=custom,
    )
    assert state.session_credential == SessionCredentialProvided(SessionId("sess"))
    assert state.persistent_credential == PersistentCredentialProvided(
        PersistentCredential("persistent")
    )


def test_missing_cookies_are_explicit_missing_states() -> None:
    _, _, _, extraction, _ = _modules()
    state = extraction.BackendAuthCredentialExtractionService().extract(
        cookies={},
        user_agent="",
        policy=policy(),
    )
    assert isinstance(state.session_credential, SessionCredentialMissing)
    assert isinstance(state.persistent_credential, PersistentCredentialMissing)
