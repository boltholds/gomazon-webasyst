from datetime import datetime
from hashlib import md5
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

pytest.importorskip("aiosqlite")

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.oauth_authorization.entities.consent_application import (
    OAuthConsentApplication,
)
from gomazon_webasyst.application.oauth_authorization.vo.client import (
    OAuthAppDisplayName,
    OAuthAppIconReference,
)
from gomazon_webasyst.composition.container import create_container_with_application_catalog
from gomazon_webasyst.composition.oauth_authorization import (
    create_oauth_authorization_components,
)
from gomazon_webasyst.composition.settings import Settings
from gomazon_webasyst.compatibility.webasyst.oauth.services.redirects import (
    LegacyUnregisteredRedirectPolicy,
)
from gomazon_webasyst.infrastructure.application_registry.in_memory_catalog import (
    InMemoryInstalledApplicationCatalog,
)
from gomazon_webasyst.infrastructure.oauth_authorization.app_catalog import (
    InMemoryOAuthConsentAppCatalog,
)
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaApiAuthCodeRow,
    WaApiTokenRow,
    WaContactRightRow,
    WaContactRow,
)
from gomazon_webasyst.presentation.http.legacy_oauth import (
    create_legacy_oauth_router,
)


SHOP = OAuthConsentApplication(
    app_id=AppId("shop"),
    display_name=OAuthAppDisplayName("Shop"),
    icon=OAuthAppIconReference("/shop.png"),
)
CRM = OAuthConsentApplication(
    app_id=AppId("crm"),
    display_name=OAuthAppDisplayName("CRM"),
    icon=OAuthAppIconReference("/crm.png"),
)


async def _build(tmp_path: Path):
    container = create_container_with_application_catalog(
        Settings(database_url=f"sqlite+aiosqlite:///{tmp_path / 'oauth.db'}"),
        installed_application_catalog=InMemoryInstalledApplicationCatalog(()),
    )
    async with container.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    sessions = async_sessionmaker(container.engine, expire_on_commit=False)
    async with sessions() as session:
        session.add_all(
            [
                WaContactRow(
                    id=42,
                    name="Admin",
                    login="admin",
                    password=md5(b"secret").hexdigest(),
                    is_user=1,
                    create_datetime=datetime(2026, 1, 1, 12, 0, 0),
                ),
                WaContactRightRow(
                    group_id=-42,
                    app_id="shop",
                    name="backend",
                    value=1,
                ),
            ]
        )
        await session.commit()

    oauth = create_oauth_authorization_components(
        session_factory=sessions,
        backend_session_bridge=container.backend_session_bridge,
        issue_authorization_code=container.issue_authorization_code,
        issue_implicit_api_access_token=container.issue_implicit_api_access_token,
        exchange_authorization_code=container.exchange_authorization_code,
        resolve_api_access_token=container.resolve_api_access_token,
        revoke_api_access_token=container.revoke_api_access_token,
        preconditions=container.api_execution.preconditions,
        credential_extractor=container.api_execution.credential_extractor,
        framework_response_renderer=container.api_execution.response_renderer,
        consent_catalog=InMemoryOAuthConsentAppCatalog((SHOP, CRM)),
        redirect_policy=LegacyUnregisteredRedirectPolicy(),
        csrf_generator=lambda: "csrf-token",
    )
    app = FastAPI()
    app.include_router(create_legacy_oauth_router(oauth))
    return container, sessions, app


def _auth_url(
    *,
    client_id: str,
    response_type: str = "code",
    redirect: bool = True,
    scope: str = "shop,crm",
) -> str:
    url = (
        f"/api.php/auth?client_id={client_id}"
        "&client_name=Demo"
        f"&response_type={response_type}"
        f"&scope={scope}"
    )
    if redirect:
        url += "&redirect_uri=https://client.test/cb"
    return url


@pytest.mark.asyncio
async def test_real_sqlite_oauth_browser_and_api_loop(tmp_path: Path) -> None:
    container, sessions, app = await _build(tmp_path)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        code_url = _auth_url(client_id="code-client")

        login_page = await client.get(code_url)
        assert login_page.status_code == 200
        assert "<form" in login_page.text
        assert client.cookies.get("_csrf") == "csrf-token"

        logged_in = await client.post(
            code_url,
            data={
                "_csrf": "csrf-token",
                "identifier": "admin",
                "password": "secret",
                "login": "1",
            },
        )
        assert logged_in.status_code == 302
        assert logged_in.headers["location"] == f"http://testserver{code_url}"
        assert client.cookies.get("gomazon_session")

        consent = await client.get(code_url)
        assert consent.status_code == 200
        assert "Shop" in consent.text
        assert "CRM" not in consent.text

        approved = await client.post(
            code_url,
            data={"_csrf": "csrf-token", "approve": "1"},
        )
        assert approved.status_code == 302
        location = approved.headers["location"]
        assert location.startswith("https://client.test/cb?code=")
        code = parse_qs(urlparse(location).query)["code"][0]
        assert len(code) == 32

        token_response = await client.post(
            "/api.php/token",
            data={
                "code": code,
                "client_id": "code-client",
                "grant_type": "authorization_code",
            },
        )
        assert token_response.status_code == 200
        access_token = token_response.json()["access_token"]
        assert len(access_token) == 32

        async with sessions() as session:
            token_row = await session.get(WaApiTokenRow, access_token)
            code_row = await session.get(WaApiAuthCodeRow, code)
            assert token_row is not None
            assert token_row.scope == "shop"
            assert code_row is not None

        revoked = await client.post(
            "/api.php/revoke",
            data={"access_token": access_token},
        )
        assert revoked.status_code == 200
        assert revoked.json() == {"access_token": access_token}

        async with sessions() as session:
            assert await session.get(WaApiTokenRow, access_token) is None

        implicit_url = _auth_url(
            client_id="implicit-client",
            response_type="token",
            scope="shop",
        )
        implicit_consent = await client.get(implicit_url)
        assert implicit_consent.status_code == 200
        implicit_approved = await client.post(
            implicit_url,
            data={"_csrf": "csrf-token", "approve": "1"},
        )
        assert implicit_approved.status_code == 302
        fragment = parse_qs(urlparse(implicit_approved.headers["location"]).fragment)
        implicit_token = fragment["access_token"][0]
        assert len(implicit_token) == 32

        bearer_only = await client.get(
            "/api.php/revoke",
            headers={"Authorization": f"Bearer {implicit_token}"},
        )
        assert bearer_only.status_code == 200
        assert bearer_only.json() == {"access_token": ""}

        async with sessions() as session:
            assert await session.get(WaApiTokenRow, implicit_token) is not None

        cancelled = await client.post(
            "/api.php/auth?response_type=code"
            "&redirect_uri=https://client.test/cancel"
            "&client_name=Cancel",
            data={"cancel": "1"},
        )
        assert cancelled.status_code == 302
        assert cancelled.headers["location"] == (
            "https://client.test/cancel?error=access_denied"
        )

        display_url = _auth_url(
            client_id="display-client",
            response_type="code",
            redirect=False,
            scope="shop",
        )
        display_consent = await client.get(display_url)
        assert display_consent.status_code == 200
        displayed = await client.post(
            display_url,
            data={"_csrf": "csrf-token", "approve": "1"},
        )
        assert displayed.status_code == 200
        assert "Authorization code" in displayed.text
        assert "csrf-token" not in displayed.text

    await container.close()
