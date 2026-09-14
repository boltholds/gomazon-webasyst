import re

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


class BackendRouteResolver:
    def resolve(
        self,
        request: BackendRouteRequest,
        seed: DispatchSeed = EmptySeed(),
        *,
        route_data: RouteData | None = None,
    ) -> ResolvedDispatch:
        controls: dict[str, str] = {
            "module": request.query.get("module", "backend"),
        }
        action = request.query.get("action")
        plugin = request.query.get("plugin")
        if action is not None:
            controls["action"] = action
        if plugin is not None:
            controls["plugin"] = plugin

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
            route_data=route_data or {},
        )
