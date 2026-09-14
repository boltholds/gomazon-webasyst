from collections.abc import Sequence

from gomazon_webasyst.contracts.dispatch import ResolvedDispatch
from gomazon_webasyst.contracts.routing import AppSettlement, ModuleRouteConstraint

from .legacy_parser import AppDispatchRule
from .patterns import RouteNotMatched, RouteMatched, match_route
from .seed_utils import CONTROL_NAMES, app_route_constraint, dispatch_from_seed, merge_seed


class AppRouteResolver:
    def resolve(
        self,
        settlement: AppSettlement,
        path: str,
        rules: Sequence[AppDispatchRule],
    ) -> ResolvedDispatch:
        for rule in rules:
            if rule.temporarily_off:
                continue
            if isinstance(settlement.constraint, ModuleRouteConstraint):
                candidate_constraint = app_route_constraint(rule.seed)
                if not isinstance(candidate_constraint, ModuleRouteConstraint):
                    continue
                if candidate_constraint.module != settlement.constraint.module:
                    continue

            pattern_result = match_route(rule.pattern, path)
            if isinstance(pattern_result, RouteNotMatched):
                continue
            if not isinstance(pattern_result, RouteMatched):
                raise TypeError(f"unsupported route match result: {type(pattern_result)!r}")
            route_match = pattern_result.match

            seed = merge_seed(settlement.seed, route_match.captures, rule.seed)
            route_data = dict(settlement.route_data)
            for key, value in route_match.captures.items():
                if key not in CONTROL_NAMES:
                    route_data.setdefault(key, value)
            route_data.update(rule.route_data)
            return ResolvedDispatch(
                request=dispatch_from_seed(settlement.app, seed, default_module="frontend"),
                route_data=route_data,
            )

        return ResolvedDispatch(
            request=dispatch_from_seed(
                settlement.app, settlement.seed, default_module="frontend"
            ),
            route_data=settlement.route_data,
        )
