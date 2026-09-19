from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest
from starlette.requests import Request
from starlette.responses import Response

from gomazon_webasyst.compatibility.webasyst.auth_http.composites.cookies import (
    BackendAuthCookieMutations,
    DeletePersistentCookie,
    DeleteSessionCookie,
    KeepPersistentCookie,
    KeepSessionCookie,
    SetPersistentCookie,
    SetSessionCookie,
)
from gomazon_webasyst.compatibility.webasyst.auth_http.services.credentials import (
    BackendAuthCredentialExtractionService,
)
from gomazon_webasyst.compatibility.webasyst.auth_http.vo.cookies import (
    BackendAuthCookiePolicy,
    CookieName,
)
from gomazon_webasyst.contracts.enums import CookieSameSite


NOW = datetime(2026, 9, 19, 12, 0, 0, tzinfo=timezone.utc)
POLICY = BackendAuthCookiePolicy(
    session_name=CookieName("gomazon_session"),
    persistent_name=CookieName("auth_token"),
    secure=True,
    path="/",
    same_site=CookieSameSite.LAX,
)


def _presentation():
    try:
        return import_module("gomazon_webasyst.presentation.http.backend_session")
    except ModuleNotFoundError as error:
        pytest.fail(f"backend session presentation helper missing: {error}")


def _request(cookie: str = "", user_agent: str = "") -> Request:
    headers = []
    if cookie:
        headers.append((b"cookie", cookie.encode()))
    if user_agent:
        headers.append((b"user-agent", user_agent.encode()))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": "/fixture",
            "raw_path": b"/fixture",
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 443),
        }
    )


def components():
    return SimpleNamespace(
        credential_extractor=BackendAuthCredentialExtractionService(),
        cookie_policy=POLICY,
    )


def test_request_normalization_reads_cookies_and_user_agent_only_at_http_boundary() -> None:
    module = _presentation()
    state = module.normalize_backend_auth_request(
        _request(
            "gomazon_session=sess-1; auth_token=persistent",
            "Browser/1.0",
        ),
        components(),
    )
    assert state.session_credential.session_id.value == "sess-1"
    assert state.persistent_credential.credential.value == "persistent"
    assert state.session_metadata.user_agent == "Browser/1.0"


def _set_cookie_headers(response: Response) -> list[str]:
    return [
        value.decode()
        for key, value in response.raw_headers
        if key.lower() == b"set-cookie"
    ]


def test_session_cookie_is_host_only_runtime_cookie_with_security_policy() -> None:
    module = _presentation()
    response = Response()
    module.apply_backend_auth_cookie_mutations(
        response,
        BackendAuthCookieMutations(
            session=SetSessionCookie("sess-1"),
            persistent=KeepPersistentCookie(),
        ),
        POLICY,
    )
    headers = _set_cookie_headers(response)
    assert len(headers) == 1
    header = headers[0]
    assert "gomazon_session=sess-1" in header
    assert "HttpOnly" in header
    assert "SameSite=lax" in header
    assert "Secure" in header
    assert "Domain=" not in header
    assert "Max-Age=" not in header
    assert "Expires=" not in header


def test_persistent_cookie_sets_max_age_and_expires_without_domain() -> None:
    module = _presentation()
    response = Response()
    module.apply_backend_auth_cookie_mutations(
        response,
        BackendAuthCookieMutations(
            session=KeepSessionCookie(),
            persistent=SetPersistentCookie(
                value="persistent",
                max_age_seconds=2592000,
                expires_at=NOW,
            ),
        ),
        POLICY,
    )
    header = _set_cookie_headers(response)[0]
    assert "auth_token=persistent" in header
    assert "Max-Age=2592000" in header
    assert "expires=" in header.lower()
    assert "Domain=" not in header
    assert "HttpOnly" in header


def test_delete_mutations_delete_both_cookie_names() -> None:
    module = _presentation()
    response = Response()
    module.apply_backend_auth_cookie_mutations(
        response,
        BackendAuthCookieMutations(
            session=DeleteSessionCookie(),
            persistent=DeletePersistentCookie(),
        ),
        POLICY,
    )
    headers = _set_cookie_headers(response)
    assert len(headers) == 2
    assert any("gomazon_session=" in item and "Max-Age=0" in item for item in headers)
    assert any("auth_token=" in item and "Max-Age=0" in item for item in headers)


def test_keep_mutations_emit_no_set_cookie_header() -> None:
    module = _presentation()
    response = Response()
    module.apply_backend_auth_cookie_mutations(
        response,
        BackendAuthCookieMutations(
            session=KeepSessionCookie(),
            persistent=KeepPersistentCookie(),
        ),
        POLICY,
    )
    assert _set_cookie_headers(response) == []


def test_main_does_not_mount_backend_session_router() -> None:
    source = Path("src/gomazon_webasyst/main.py").read_text()
    assert "backend_session_router" not in source
    assert "create_backend_session_router" not in source
