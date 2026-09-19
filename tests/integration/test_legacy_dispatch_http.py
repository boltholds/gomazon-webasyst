from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from gomazon_webasyst.application.app_values import AppId
from gomazon_webasyst.application.application_registry import (
    ApplicationCatalog,
    InstallationManifest,
    InstalledApplication,
    StaticApplicationRegistry,
)
from gomazon_webasyst.compatibility.webasyst.dispatch.registry import (
    InMemoryHandlerRegistry,
)
from gomazon_webasyst.compatibility.webasyst.dispatch.resolver import DispatchResolver
from gomazon_webasyst.compatibility.webasyst.dispatch.strategies import DispatchStrategyRegistry
from gomazon_webasyst.compatibility.webasyst.routing.app_resolver import AppRouteResolver
from gomazon_webasyst.compatibility.webasyst.routing.backend_resolver import BackendRouteResolver
from gomazon_webasyst.compatibility.webasyst.routing.legacy_parser import (
    parse_app_routes,
    parse_system_routes,
)
from gomazon_webasyst.compatibility.webasyst.routing.system_resolver import SystemRouteResolver
from gomazon_webasyst.compatibility.webasyst.service import LegacyCompatibilityService
from gomazon_webasyst.contracts.applications import ApplicationDescriptor
from gomazon_webasyst.contracts.dispatch import (
    ActionHandlerKey,
    AppNamespace,
)
from gomazon_webasyst.presentation.http.legacy_dispatch import create_legacy_compatibility_router


def build_app() -> FastAPI:
    system = SystemRouteResolver(
        parse_system_routes(
            {
                "example.com": [
                    {"url": "old/*", "redirect": "/new/*"},
                    {"url": "blog/*", "app": "blog"},
                    {"url": "missing/*", "app": "missing"},
                ]
            }
        )
    )
    app_routes = {
        "blog": parse_app_routes(
            "blog",
            {"post/<id:\\d+>/": "frontend/post"},
        )
    }

    handlers = InMemoryHandlerRegistry()
    blog_key = ActionHandlerKey(
        namespace=AppNamespace(app="blog"), module="frontend", action="post"
    )
    team_key = ActionHandlerKey(
        namespace=AppNamespace(app="team"), module="users", action="list"
    )
    handlers.register_action(blog_key, "blog-post")
    handlers.register_action(team_key, "team-users-list")

    applications = StaticApplicationRegistry(
        ApplicationCatalog(
            applications=(
                ApplicationDescriptor(id=AppId("blog"), name="Blog"),
                ApplicationDescriptor(id=AppId("team"), name="Team"),
            ),
        ),
        InstallationManifest(
            apps=(
                InstalledApplication(AppId("blog")),
                InstalledApplication(AppId("team")),
            )
        ),
    )
    resolver = DispatchResolver(handlers, applications)
    strategies = DispatchStrategyRegistry(resolver)
    service = LegacyCompatibilityService(
        system_resolver=system,
        app_resolver=AppRouteResolver(),
        backend_resolver=BackendRouteResolver(),
        app_routes=app_routes,
        strategies=strategies,
    )

    async def blog_post(outcome):
        return {
            "handler": outcome.target.handler_id,
            "id": outcome.dispatch.route_data["id"],
            "target_kind": outcome.target.kind,
        }

    async def team_users(outcome):
        return {
            "handler": outcome.target.handler_id,
            "target_kind": outcome.target.kind,
        }

    app = FastAPI()
    app.include_router(
        create_legacy_compatibility_router(
            service,
            handlers={
                "blog-post": blog_post,
                "team-users-list": team_users,
            },
        )
    )
    return app


async def test_frontend_redirect_preserves_query_string() -> None:
    app = build_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://example.com"
    ) as client:
        response = await client.get("/old/a/b?x=1", follow_redirects=False)
    assert response.status_code == 301
    assert response.headers["location"] == "/new/a/b?x=1"


async def test_frontend_route_resolves_handler_and_route_data() -> None:
    app = build_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://example.com"
    ) as client:
        response = await client.get("/blog/post/42/")
    assert response.status_code == 200
    assert response.json() == {
        "handler": "blog-post",
        "id": "42",
        "target_kind": "single_action",
    }


async def test_backend_query_normalization_resolves_handler() -> None:
    app = build_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://example.com"
    ) as client:
        response = await client.get("/webasyst/team/?module=users&action=list")
    assert response.status_code == 200
    assert response.json()["handler"] == "team-users-list"


async def test_invalid_backend_dispatch_parameter_maps_to_400() -> None:
    app = build_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://example.com"
    ) as client:
        response = await client.get("/webasyst/team/?module=../users")
    assert response.status_code == 400


async def test_missing_registered_target_maps_to_404() -> None:
    app = build_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://example.com"
    ) as client:
        response = await client.get("/missing/path")
    assert response.status_code == 404
