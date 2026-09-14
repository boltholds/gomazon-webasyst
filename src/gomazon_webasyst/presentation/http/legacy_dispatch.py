from collections.abc import Awaitable, Callable, Mapping
import inspect
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from gomazon_webasyst.compatibility.webasyst.dispatch.errors import (
    DispatchTargetNotFound,
    PluginUnavailable,
)
from gomazon_webasyst.compatibility.webasyst.routing.errors import (
    InvalidDispatchParameter,
    RouteNotFound,
)
from gomazon_webasyst.compatibility.webasyst.service import LegacyCompatibilityService
from gomazon_webasyst.contracts.dispatch import HandlerDispatchOutcome
from gomazon_webasyst.contracts.routing import (
    BackendRouteRequest,
    FrontendRouteRequest,
    RedirectSettlement,
)


LegacyHandler = Callable[[HandlerDispatchOutcome], Any | Awaitable[Any]]
_HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]


def create_legacy_compatibility_router(
    service: LegacyCompatibilityService,
    *,
    handlers: Mapping[str, LegacyHandler],
) -> APIRouter:
    router = APIRouter()

    async def execute(outcome: HandlerDispatchOutcome) -> Response:
        if outcome.target.handler_id not in handlers:
            return JSONResponse({"detail": "Legacy handler not registered"}, status_code=404)
        handler = handlers[outcome.target.handler_id]
        result = handler(outcome)
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, Response):
            return result
        return JSONResponse(result)

    @router.api_route("/webasyst/{app}/{path:path}", methods=_HTTP_METHODS)
    async def backend(request: Request, app: str, path: str) -> Response:
        try:
            outcome = service.resolve_backend(
                BackendRouteRequest(
                    app=app,
                    path=path,
                    query=dict(request.query_params),
                )
            )
            return await execute(outcome)
        except InvalidDispatchParameter as exc:
            return JSONResponse({"detail": str(exc)}, status_code=400)
        except (DispatchTargetNotFound, PluginUnavailable) as exc:
            return JSONResponse({"detail": str(exc)}, status_code=404)

    @router.api_route("/{path:path}", methods=_HTTP_METHODS)
    async def frontend(request: Request, path: str) -> Response:
        host = request.url.hostname or request.headers.get("host", "")
        try:
            outcome = service.resolve_frontend(
                FrontendRouteRequest(
                    domain=host,
                    path=path,
                    query=dict(request.query_params),
                )
            )
            if isinstance(outcome, RedirectSettlement):
                return RedirectResponse(
                    url=outcome.location,
                    status_code=outcome.status_code,
                )
            return await execute(outcome)
        except InvalidDispatchParameter as exc:
            return JSONResponse({"detail": str(exc)}, status_code=400)
        except (RouteNotFound, DispatchTargetNotFound, PluginUnavailable) as exc:
            return JSONResponse({"detail": str(exc)}, status_code=404)

    return router
