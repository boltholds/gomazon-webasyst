from collections.abc import Sequence

from gomazon_webasyst.contracts.dispatch import ResolvedDispatch
from gomazon_webasyst.contracts.routing import AppSettlement, ModuleRouteConstraint

from .legacy_parser import AppDispatchRule
from .patterns import match_route
from .seed_utils import CONTROL_NAMES, dispatch_from_seed, explicit_module, merge_seed


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
                candidate_module = explicit_module(rule.seed)
                if candidate_module != settlement.constraint.module:
                    continue

            route_match = match_route(rule.pattern, path)
            if route_match is None:
                continue

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
