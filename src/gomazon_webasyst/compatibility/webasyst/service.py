from collections.abc import Mapping, Sequence

from gomazon_webasyst.compatibility.webasyst.dispatch.strategies import DispatchStrategyRegistry
from gomazon_webasyst.compatibility.webasyst.routing.app_resolver import AppRouteResolver
from gomazon_webasyst.compatibility.webasyst.routing.backend_resolver import BackendRouteResolver
from gomazon_webasyst.compatibility.webasyst.routing.legacy_parser import AppDispatchRule
from gomazon_webasyst.compatibility.webasyst.routing.system_resolver import SystemRouteResolver
from gomazon_webasyst.contracts.dispatch import HandlerDispatchOutcome, LegacyDispatchOutcome
from gomazon_webasyst.contracts.routing import (
    BackendRouteRequest,
    DispatchSeed,
    EmptySeed,
    FrontendRouteRequest,
    RedirectSettlement,
    RouteData,
)


class LegacyCompatibilityService:
    def __init__(
        self,
        *,
        system_resolver: SystemRouteResolver,
        app_resolver: AppRouteResolver,
        backend_resolver: BackendRouteResolver,
        app_routes: Mapping[str, Sequence[AppDispatchRule]],
        strategies: DispatchStrategyRegistry,
    ) -> None:
        self._system = system_resolver
        self._app = app_resolver
        self._backend = backend_resolver
        self._app_routes = app_routes
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
        route_data: RouteData | None = None,
    ) -> HandlerDispatchOutcome:
        resolved = self._backend.resolve(request, seed, route_data=route_data)
        strategy = self._strategies.for_request(resolved.request)
        target = strategy.resolve(resolved.request)
        return HandlerDispatchOutcome(dispatch=resolved, target=target)
