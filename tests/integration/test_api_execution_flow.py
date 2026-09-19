from datetime import datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_execution.composites.results import ApiMethodSucceeded
from gomazon_webasyst.application.api_execution.entities.method_definition import ApiMethodDefinition
from gomazon_webasyst.application.api_execution.vo.method import ApiHttpMethod, ApiMethodName, ApiMethodTarget
from gomazon_webasyst.compatibility.webasyst.api.services.license import AllowAllAppLicensePolicy
from gomazon_webasyst.composition.api_credentials import create_api_credential_use_cases
from gomazon_webasyst.composition.api_execution import create_api_execution_components
from gomazon_webasyst.infrastructure.api_execution.app_directory import InMemoryInstalledAppDirectory
from gomazon_webasyst.infrastructure.api_execution.method_registry import InMemoryApiMethodRegistry
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.base import Base
from gomazon_webasyst.infrastructure.persistence.sqlalchemy.models import (
    WaApiTokenRow,
    WaContactRightRow,
    WaContactRow,
)
from gomazon_webasyst.presentation.http.legacy_api import create_legacy_api_router


TOKEN = "a" * 32
SCOPE_TOKEN = "b" * 32
DENIED_TOKEN = "c" * 32


class FixtureHandler:
    def __init__(self) -> None:
        self.calls = []

    async def execute(self, context, parameters):
        self.calls.append((context, parameters))
        return ApiMethodSucceeded(
            payload={
                "_element": "ignored",
                "items": [{"id": 1}],
                "app": context.target.app_id.value,
                "method": context.target.method.value,
            },
            status_code=200,
        )


async def _seed(sessions) -> datetime:
    old = datetime(2020, 1, 1, 0, 0, 0)
    async with sessions() as session:
        session.add_all([
            WaContactRow(
                id=42,
                name="Allowed",
                firstname="Allowed",
                is_user=1,
                login="allowed",
                create_datetime=old,
                last_datetime=old,
            ),
            WaContactRow(
                id=43,
                name="Denied",
                firstname="Denied",
                is_user=1,
                login="denied",
                create_datetime=old,
                last_datetime=old,
            ),
            WaContactRightRow(
                group_id=-42,
                app_id="shop",
                name="backend",
                value=1,
            ),
            WaApiTokenRow(
                contact_id=42,
                client_id="client",
                token=TOKEN,
                scope="shop",
                create_datetime=old,
                last_use_datetime=None,
                expires=None,
            ),
            WaApiTokenRow(
                contact_id=42,
                client_id="scope-client",
                token=SCOPE_TOKEN,
                scope="site",
                create_datetime=old,
                last_use_datetime=None,
                expires=None,
            ),
            WaApiTokenRow(
                contact_id=43,
                client_id="denied-client",
                token=DENIED_TOKEN,
                scope="shop",
                create_datetime=old,
                last_use_datetime=None,
                expires=None,
            ),
        ])
        await session.commit()
    return old


@pytest.mark.asyncio
async def test_api_execution_real_sqlite_asgi_vertical_flow() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    old = await _seed(sessions)

    credentials = create_api_credential_use_cases(sessions)
    registry = InMemoryApiMethodRegistry()
    handler = FixtureHandler()
    registry.register(
        ApiMethodDefinition(
            target=ApiMethodTarget(AppId("shop"), ApiMethodName("ping")),
            allowed_methods=frozenset({ApiHttpMethod("GET"), ApiHttpMethod("POST")}),
            handler=handler,
        )
    )
    components = create_api_execution_components(
        session_factory=sessions,
        resolve_api_access_token=credentials.resolve_api_access_token,
        method_registry=registry,
        installed_app_directory=InMemoryInstalledAppDirectory(frozenset({AppId("shop")})),
        license_policy=AllowAllAppLicensePolicy(),
        api_enabled=True,
        disable_message="",
        force_https=False,
    )
    app = FastAPI()
    app.include_router(create_legacy_api_router(components))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        root = await client.get(f"/api.php?app=shop&method=ping&access_token={TOKEN}")
        slash = await client.get(f"/api.php/shop/ping?access_token={TOKEN}")
        dotted = await client.get(f"/api.php/shop.ping?access_token={TOKEN}")
        bearer = await client.get(
            "/api.php/shop/ping",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        xml = await client.get(f"/api.php/shop/ping?access_token={TOKEN}&format=xml")
        scope_denied = await client.get(f"/api.php/shop/ping?access_token={SCOPE_TOKEN}")
        access_denied = await client.get(f"/api.php/shop/ping?access_token={DENIED_TOKEN}")
        method_missing = await client.get(f"/api.php/shop/missing?access_token={TOKEN}")
        app_missing = await client.get(f"/api.php/site/ping?access_token={SCOPE_TOKEN}")
        verb_denied = await client.delete(f"/api.php/shop/ping?access_token={TOKEN}")
        jsonp_error = await client.get(
            f"/api.php/shop/missing?access_token={TOKEN}&callback=cb"
        )
        reserved = await client.get("/api.php/auth")

    for response in (root, slash, dotted, bearer):
        assert response.status_code == 200
        assert response.json() == {
            "items": [{"id": 1}],
            "app": "shop",
            "method": "ping",
        }

    assert xml.status_code == 200
    assert "<response>" in xml.text
    assert "<item><id>1</id></item>" in xml.text

    assert scope_denied.status_code == 403
    assert scope_denied.json()["error"] == "access_denied"
    assert access_denied.status_code == 403
    assert access_denied.json()["error"] == "access_denied"
    assert method_missing.status_code == 404
    assert method_missing.json()["error"] == "invalid_method"
    assert app_missing.status_code == 400
    assert app_missing.json()["error"] == "app_not_installed"
    assert verb_denied.status_code == 405
    assert verb_denied.json()["error"] == "invalid_request"
    assert jsonp_error.status_code == 200
    assert jsonp_error.text.startswith("cb(")
    assert reserved.status_code == 404

    async with sessions() as session:
        token_row = await session.get(WaApiTokenRow, TOKEN)
        contact = await session.get(WaContactRow, 42)
        assert token_row.last_use_datetime is not None
        assert token_row.last_use_datetime > old
        assert contact.last_datetime is not None
        assert contact.last_datetime > old

    assert len(handler.calls) == 5
    await engine.dispose()
