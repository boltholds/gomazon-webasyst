from collections.abc import Mapping, Sequence
from types import MappingProxyType

from pydantic import JsonValue

from gomazon_webasyst.compatibility.webasyst.dispatch.strategies import DispatchStrategyRegistry
from gomazon_webasyst.compatibility.webasyst.routing.app_resolver import AppRouteResolver
from gomazon_webasyst.compatibility.webasyst.routing.backend_app_resolver import (
    BackendAppRouteMatched,
    BackendAppRouteResolver,
)
from gomazon_webasyst.compatibility.webasyst.routing.backend_resolver import BackendRouteResolver
from gomazon_webasyst.compatibility.webasyst.routing.legacy_parser import AppDispatchRule
from gomazon_webasyst.compatibility.webasyst.routing.system_resolver import SystemRouteResolver
from gomazon_webasyst.compatibility.webasyst.routing.errors import RouteNotFound
from gomazon_webasyst.contracts.dispatch import HandlerDispatchOutcome, LegacyDispatchOutcome
from gomazon_webasyst.contracts.routing import (
    BackendRouteRequest,
    DispatchSeed,
    EmptySeed,
    FrontendRouteRequest,
    RedirectSettlement,
    RouteData,
)


_EMPTY_ROUTE_DATA: Mapping[str, JsonValue] = MappingProxyType({})
_EMPTY_BACKEND_ROUTES: Mapping[str, Sequence[AppDispatchRule]] = MappingProxyType({})


class LegacyCompatibilityService:
    def __init__(
        self,
        *,
        system_resolver: SystemRouteResolver,
        app_resolver: AppRouteResolver,
        backend_resolver: BackendRouteResolver,
        app_routes: Mapping[str, Sequence[AppDispatchRule]],
        strategies: DispatchStrategyRegistry,
        backend_app_resolver: BackendAppRouteResolver = BackendAppRouteResolver(),
        backend_routes: Mapping[
            str, Sequence[AppDispatchRule]
        ] = _EMPTY_BACKEND_ROUTES,
    ) -> None:
        self._system = system_resolver
        self._app = app_resolver
        self._backend = backend_resolver
        self._backend_app = backend_app_resolver
        self._app_routes = app_routes
        self._backend_routes = backend_routes
        self._strategies = strategies

    def resolve_frontend(self, request: FrontendRouteRequest) -> LegacyDispatchOutcome:
        settlement = self._system.resolve(request)
        if isinstance(settlement, RedirectSettlement):
            return settlement

        resolved = self._app.resolve(
            settlement,
            settlement.remaining_path,
            self._app_routes.get(settlement.app, ()),
        )
        strategy = self._strategies.for_request(resolved.request)
        target = strategy.resolve(resolved.request)
        return HandlerDispatchOutcome(dispatch=resolved, target=target)

    def resolve_backend(
        self,
        request: BackendRouteRequest,
        seed: DispatchSeed = EmptySeed(),
        *,
        route_data: Mapping[str, JsonValue] = _EMPTY_ROUTE_DATA,
    ) -> HandlerDispatchOutcome:
        effective_seed = seed
        effective_route_data = route_data

        if (
            isinstance(seed, EmptySeed)
            and request.app in self._backend_routes
            and self._backend_route_query_controls_are_empty(request)
        ):
            route_resolution = self._backend_app.resolve(
                request.path,
                tuple(self._backend_routes[request.app]),
            )
            if not isinstance(route_resolution, BackendAppRouteMatched):
                raise RouteNotFound(
                    f"no backend route matched {request.app}:{request.path}"
                )
            effective_seed = route_resolution.seed
            effective_route_data = route_resolution.route_data

        resolved = self._backend.resolve(
            request,
            effective_seed,
            route_data=effective_route_data,
        )
        strategy = self._strategies.for_request(resolved.request)
        target = strategy.resolve(resolved.request)
        return HandlerDispatchOutcome(dispatch=resolved, target=target)

    @staticmethod
    def _backend_route_query_controls_are_empty(
        request: BackendRouteRequest,
    ) -> bool:
        return all(
            request.query.get(name, "") in {"", "0"}
            for name in ("module", "plugin")
        )
