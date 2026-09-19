from datetime import datetime
from hashlib import md5
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import SecretStr

pytest.importorskip("aiosqlite")

from gomazon_webasyst.application.backend_session_bridge.composites.requests import (
    BackendCurrentSubjectRequest,
    BackendLogoutRequest,
    BackendPasswordLoginRequest,
)
from gomazon_webasyst.composition.container import create_container_with_application_catalog
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.contracts.auth import (
    BackendPasswordCredentials,
    LoginPolicyContext,
)
from gomazon_webasyst.contracts.backend_session_bridge import (
    BackendPasswordLoginRejected,
    CurrentBackendSubjectResolved,
)
from gomazon_webasyst.contracts.enums import RememberIntent
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import WaContactRow
from gomazon_webasyst.presentation.http.backend_session import (
    apply_backend_auth_cookie_mutations,
    normalize_backend_auth_request,
)


async def _seed_container(
    db_path: Path,
    *,
    persistent_login_enabled: bool = True,
):
    container = create_container_with_application_catalog(
        Settings(
            database_url=f"sqlite+aiosqlite:///{db_path}",
            persistent_login_enabled=persistent_login_enabled,
        ),
        installed_application_catalog=InMemoryInstalledApplicationCatalog(()),
    )
    async with container.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    from sqlalchemy.ext.asyncio import async_sessionmaker

    sessions = async_sessionmaker(container.engine, expire_on_commit=False)
    async with sessions() as session:
        existing = await session.get(WaContactRow, 42)
        if existing is None:
            session.add(
                WaContactRow(
                    id=42,
                    name="Admin",
                    login="admin",
                    password=md5(b"secret").hexdigest(),
                    is_user=1,
                    create_datetime=datetime(2026, 1, 1, 12, 0, 0),
                )
            )
            await session.commit()
    return container


def _fixture_app(container) -> FastAPI:
    app = FastAPI()
    bridge = container.backend_session_bridge

    @app.post("/fixture/login")
    async def login(request: Request) -> Response:
        state = normalize_backend_auth_request(request, bridge)
        remember = (
            RememberIntent.PERSIST
            if request.query_params.get("remember") == "persist"
            else RememberIntent.SESSION_ONLY
        )
        result = await bridge.password_login_flow(
            BackendPasswordLoginRequest(
                credentials=BackendPasswordCredentials(
                    identifier="admin",
                    password=SecretStr("secret"),
                    login_context=LoginPolicyContext(enabled_schemes=("login",)),
                    session_metadata=state.session_metadata,
                ),
                remember_intent=remember,
                persistent_login_mode=bridge.persistent_login_mode,
            )
        )
        if isinstance(result, BackendPasswordLoginRejected):
            return JSONResponse({"authenticated": False}, status_code=401)

        response = JSONResponse({"subject_id": result.subject.id})
        mutations = bridge.cookie_mutation_service.plan(
            session_disposition=result.session_disposition,
            persistent_disposition=result.persistent_disposition,
        )
        apply_backend_auth_cookie_mutations(response, mutations, bridge.cookie_policy)
        return response

    @app.get("/fixture/current")
    async def current(request: Request) -> Response:
        state = normalize_backend_auth_request(request, bridge)
        result = await bridge.current_subject_flow(
            BackendCurrentSubjectRequest(
                session_credential=state.session_credential,
                persistent_credential=state.persistent_credential,
                session_metadata=state.session_metadata,
                persistent_login_mode=bridge.persistent_login_mode,
            )
        )
        if isinstance(result, CurrentBackendSubjectResolved):
            response = JSONResponse({"subject_id": result.subject.id})
        else:
            response = JSONResponse({"authenticated": False}, status_code=401)

        mutations = bridge.cookie_mutation_service.plan(
            session_disposition=result.session_disposition,
            persistent_disposition=result.persistent_disposition,
        )
        apply_backend_auth_cookie_mutations(response, mutations, bridge.cookie_policy)
        return response

    @app.post("/fixture/logout")
    async def logout(request: Request) -> Response:
        state = normalize_backend_auth_request(request, bridge)
        result = await bridge.logout_flow(
            BackendLogoutRequest(session_credential=state.session_credential)
        )
        response = Response(status_code=204)
        mutations = bridge.cookie_mutation_service.plan(
            session_disposition=result.session_disposition,
            persistent_disposition=result.persistent_disposition,
        )
        apply_backend_auth_cookie_mutations(response, mutations, bridge.cookie_policy)
        return response

    return app


def _set_cookie_headers(response: httpx.Response) -> list[str]:
    return response.headers.get_list("set-cookie")


@pytest.mark.asyncio
async def test_persistent_browser_flow_restores_stale_session_and_logout_clears_cookies(
    tmp_path: Path,
) -> None:
    container = await _seed_container(tmp_path / "bridge.db")
    app = _fixture_app(container)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        login = await client.post(
            "/fixture/login?remember=persist",
            headers={"User-Agent": "Browser/1.0"},
        )
        assert login.status_code == 200
        assert login.json()["subject_id"] == 42

        set_cookies = _set_cookie_headers(login)
        session_header = next(x for x in set_cookies if x.startswith("gomazon_session="))
        persistent_header = next(x for x in set_cookies if x.startswith("auth_token="))
        assert "HttpOnly" in session_header
        assert "SameSite=lax" in session_header
        assert "Domain=" not in session_header
        assert "Max-Age=" not in session_header
        assert "Expires=" not in session_header
        assert "HttpOnly" in persistent_header
        assert "SameSite=lax" in persistent_header
        assert "Max-Age=2592000" in persistent_header
        assert "expires=" in persistent_header.lower()

        current = await client.get("/fixture/current")
        assert current.status_code == 200
        assert current.json()["subject_id"] == 42

        auth_token = client.cookies.get("auth_token")
        assert auth_token

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as restored_client:
        restored = await restored_client.get(
            "/fixture/current",
            headers={
                "Cookie": (
                    f"gomazon_session=stale; auth_token={auth_token}"
                )
            },
        )
        assert restored.status_code == 200
        assert restored.json()["subject_id"] == 42
        restored_session = restored_client.cookies.get("gomazon_session")
        assert restored_session
        assert restored_session != "stale"
        assert restored_client.cookies.get("auth_token") == auth_token

        logout = await restored_client.post("/fixture/logout")
        assert logout.status_code == 204
        assert restored_client.cookies.get("gomazon_session") is None
        assert restored_client.cookies.get("auth_token") is None

        after = await restored_client.get("/fixture/current")
        assert after.status_code == 401

    await container.close()


@pytest.mark.asyncio
async def test_session_only_login_preserves_existing_persistent_cookie(
    tmp_path: Path,
) -> None:
    container = await _seed_container(tmp_path / "session-only.db")
    app = _fixture_app(container)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        first = await client.post("/fixture/login?remember=persist")
        assert first.status_code == 200
        persistent_before = client.cookies.get("auth_token")
        assert persistent_before

        second = await client.post("/fixture/login?remember=session")
        assert second.status_code == 200
        assert client.cookies.get("auth_token") == persistent_before
        assert not any(
            header.startswith("auth_token=")
            for header in _set_cookie_headers(second)
        )

    await container.close()


@pytest.mark.asyncio
async def test_persistent_disabled_clears_only_stale_session_and_keeps_auth_token(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "disabled.db"
    enabled = await _seed_container(db_path)
    enabled_app = _fixture_app(enabled)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=enabled_app),
        base_url="http://testserver",
    ) as client:
        issued = await client.post("/fixture/login?remember=persist")
        assert issued.status_code == 200
        auth_token = client.cookies.get("auth_token")
        assert auth_token

    await enabled.close()

    disabled = await _seed_container(
        db_path,
        persistent_login_enabled=False,
    )
    disabled_app = _fixture_app(disabled)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=disabled_app),
        base_url="http://testserver",
    ) as client:
        current = await client.get(
            "/fixture/current",
            headers={
                "Cookie": (
                    f"gomazon_session=stale; auth_token={auth_token}"
                )
            },
        )
        assert current.status_code == 401
        headers = _set_cookie_headers(current)
        assert any(
            header.startswith("gomazon_session=") and "Max-Age=0" in header
            for header in headers
        )
        assert not any(header.startswith("auth_token=") for header in headers)

    await disabled.close()
