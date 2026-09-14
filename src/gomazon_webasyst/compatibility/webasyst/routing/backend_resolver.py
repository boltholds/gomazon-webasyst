import re
from collections.abc import Mapping
from types import MappingProxyType

from pydantic import JsonValue

from gomazon_webasyst.contracts.dispatch import ResolvedDispatch
from gomazon_webasyst.contracts.routing import (
    BackendRouteRequest,
    DispatchSeed,
    EmptySeed,
    RouteData,
)

from .errors import InvalidDispatchParameter
from .seed_utils import dispatch_from_seed, seed_from_controls, seed_to_controls


_VALID_DISPATCH_PARAM = re.compile(r"^[a-z_][a-z0-9_]*$", re.IGNORECASE)
_EMPTY_ROUTE_DATA: Mapping[str, JsonValue] = MappingProxyType({})


class BackendRouteResolver:
    def resolve(
        self,
        request: BackendRouteRequest,
        seed: DispatchSeed = EmptySeed(),
        *,
        route_data: Mapping[str, JsonValue] = _EMPTY_ROUTE_DATA,
    ) -> ResolvedDispatch:
        controls: dict[str, str] = {
            "module": request.query.get("module", "backend"),
        }
        if "action" in request.query:
            controls["action"] = request.query["action"]
        if "plugin" in request.query:
            controls["plugin"] = request.query["plugin"]

        controls.update(seed_to_controls(seed))

        for index, name in enumerate(("plugin", "module", "action")):
            value = controls.get(name)
            if value and _VALID_DISPATCH_PARAM.fullmatch(value) is None:
                raise InvalidDispatchParameter(
                    f"Bad parameters ({index}): {name}={value!r}"
                )

        normalized_seed = seed_from_controls(controls)
        return ResolvedDispatch(
            request=dispatch_from_seed(
                request.app, normalized_seed, default_module="backend"
            ),
            route_data=dict(route_data),
        )
