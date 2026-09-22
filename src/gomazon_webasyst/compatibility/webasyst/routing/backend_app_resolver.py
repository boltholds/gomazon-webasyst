from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.compatibility.webasyst.routing.legacy_parser import (
    AppDispatchRule,
)
from gomazon_webasyst.compatibility.webasyst.routing.patterns import (
    RouteMatched,
    match_route,
)
from gomazon_webasyst.compatibility.webasyst.routing.seed_utils import (
    CONTROL_NAMES,
    merge_seed,
)
from gomazon_webasyst.contracts.routing import (
    DispatchSeed,
    EmptySeed,
    RouteData,
)


@dataclass(slots=True, frozen=True)
class BackendAppRouteMatched:
    seed: DispatchSeed
    route_data: RouteData


@dataclass(slots=True, frozen=True)
class BackendAppRouteNotMatched:
    pass


BackendAppRouteResolution: TypeAlias = (
    BackendAppRouteMatched | BackendAppRouteNotMatched
)


class BackendAppRouteResolver:
    def resolve(
        self,
        path: str,
        rules: tuple[AppDispatchRule, ...],
    ) -> BackendAppRouteResolution:
        for rule in rules:
            if rule.temporarily_off:
                continue
            result = match_route(rule.pattern, path)
            if not isinstance(result, RouteMatched):
                continue

            captures = result.match.captures
            seed = merge_seed(EmptySeed(), captures, rule.seed)
            route_data = {
                key: value
                for key, value in captures.items()
                if key not in CONTROL_NAMES
            }
            route_data.update(rule.route_data)
            return BackendAppRouteMatched(
                seed=seed,
                route_data=route_data,
            )
        return BackendAppRouteNotMatched()
