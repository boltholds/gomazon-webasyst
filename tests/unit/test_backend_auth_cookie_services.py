from datetime import datetime, timedelta
from importlib import import_module

import pytest

from gomazon_webasyst.application.auth_values import SessionId
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
CREDENTIAL = PersistentCredential("persistent")
LIFETIME = PersistentCredentialLifetime(timedelta(days=30))


def _modules():
    try:
        cookies = import_module(
            "gomazon_webasyst.compatibility.webasyst.auth_http.vo.cookies"
        )
        mutations = import_module(
            "gomazon_webasyst.compatibility.webasyst.auth_http.composites.cookies"
        )
        planner = import_module(
            "gomazon_webasyst.compatibility.webasyst.auth_http.services.cookie_mutations"
        )
        return cookies, mutations, planner
    except ModuleNotFoundError as error:
        pytest.fail(f"auth http cookie package missing: {error}")


def test_cookie_policy_is_host_only_and_cookie_names_are_validated() -> None:
    cookies, _, _ = _modules()
    policy = cookies.BackendAuthCookiePolicy(
        session_name=cookies.CookieName("gomazon_session"),
        persistent_name=cookies.CookieName("auth_token"),
        secure=True,
        path="/",
        same_site=cookies.CookieSameSite.LAX,
    )
    assert policy.path == "/"
    assert policy.secure is True
    assert not hasattr(policy, "domain")
    with pytest.raises(ValueError):
        cookies.CookieName("")
    with pytest.raises(ValueError):
        cookies.CookieName("bad cookie")


@pytest.mark.parametrize(
    ("session_disposition", "expected_type"),
    [
        (IssueSessionCredential(session_id=SessionId("sess-1")), "SetSessionCookie"),
        (ClearSessionCredential(), "DeleteSessionCookie"),
        (KeepSessionCredential(), "KeepSessionCookie"),
    ],
)
def test_session_disposition_maps_one_to_one(session_disposition, expected_type) -> None:
    _, mutations, planner = _modules()
    service = planner.BackendAuthCookieMutationService(clock=lambda: NOW)
    result = service.plan(
        session_disposition=session_disposition,
        persistent_disposition=KeepPersistentCredential(),
    )
    assert type(result.session).__name__ == expected_type
    if expected_type == "SetSessionCookie":
        assert result.session.value == "sess-1"


def test_persistent_refresh_sets_exact_lifetime_and_expiry() -> None:
    _, mutations, planner = _modules()
    result = planner.BackendAuthCookieMutationService(clock=lambda: NOW).plan(
        session_disposition=KeepSessionCredential(),
        persistent_disposition=RefreshPersistentCredential(
            credential=CREDENTIAL,
            lifetime=LIFETIME,
        ),
    )
    assert isinstance(result.persistent, mutations.SetPersistentCookie)
    assert result.persistent.value == "persistent"
    assert result.persistent.max_age_seconds == 2592000
    assert result.persistent.expires_at == NOW + timedelta(days=30)


@pytest.mark.parametrize(
    ("persistent_disposition", "expected_type"),
    [
        (ClearPersistentCredential(), "DeletePersistentCookie"),
        (KeepPersistentCredential(), "KeepPersistentCookie"),
    ],
)
def test_persistent_clear_and_keep_map_one_to_one(
    persistent_disposition,
    expected_type,
) -> None:
    _, _, planner = _modules()
    result = planner.BackendAuthCookieMutationService(clock=lambda: NOW).plan(
        session_disposition=KeepSessionCredential(),
        persistent_disposition=persistent_disposition,
    )
    assert type(result.persistent).__name__ == expected_type


def test_non_positive_persistent_lifetime_is_rejected() -> None:
    _, _, planner = _modules()
    with pytest.raises(ValueError, match="positive"):
        planner.BackendAuthCookieMutationService(clock=lambda: NOW).plan(
            session_disposition=KeepSessionCredential(),
            persistent_disposition=RefreshPersistentCredential(
                credential=CREDENTIAL,
                lifetime=PersistentCredentialLifetime(timedelta(seconds=0)),
            ),
        )
