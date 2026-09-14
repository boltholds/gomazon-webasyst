from __future__ import annotations

from urllib.parse import unquote_to_bytes, urlencode

from gomazon_webasyst.contracts.routing import (
    AnyAppRouteConstraint,
    AppSettlement,
    FrontendRouteRequest,
    ModuleRouteConstraint,
    RedirectSettlement,
    SettlementResolution,
)

from .errors import RouteNotFound
from .legacy_parser import SystemAppRule, SystemRedirectRule, SystemRouteRule, SystemRouteTable
from .patterns import RouteMatch, match_route
from .seed_utils import CONTROL_NAMES, EmptySeed, explicit_module, merge_seed


class SystemRouteResolver:
    def __init__(self, table: SystemRouteTable):
        self._table = table

    def resolve(self, request: FrontendRouteRequest) -> SettlementResolution:
        path = self._decode_path(request.path)
        rules = self._table.routes.get(request.domain)
        if rules is None:
            rules = self._table.routes.get("default", ())

        first = self._match_once(rules, path)
        if first is not None:
            rule, route_match = first
            if isinstance(rule, SystemRedirectRule):
                return self._redirect(rule, route_match, request)

        retry = False
        if first is None:
            retry = not path.endswith("/")
        else:
            rule, _ = first
            retry = (
                rule.pattern.source == "*"
                and bool(path)
                and "." not in path[-5:]
                and not path.endswith("/")
            )

        if retry:
            second = self._match_once(rules, path + "/")
            if second is not None:
                second_rule, second_match = second
                if isinstance(second_rule, SystemRedirectRule):
                    return self._redirect(second_rule, second_match, request)
                if first is None or second_rule.pattern.source != "*":
                    return RedirectSettlement(location="/" + path + "/", status_code=301)

        if first is None:
            raise RouteNotFound(f"no Webasyst settlement for {request.domain}/{path}")

        rule, route_match = first
        return self._app_settlement(rule, route_match, path)

    @staticmethod
    def _decode_path(path: str) -> str:
        try:
            return unquote_to_bytes(path).decode("utf-8")
        except UnicodeDecodeError:
            return path

    @staticmethod
    def _match_once(
        rules: tuple[SystemRouteRule, ...], path: str
    ) -> tuple[SystemRouteRule, RouteMatch] | None:
        for rule in rules:
            if rule.temporarily_off:
                continue
            if isinstance(rule, SystemRedirectRule) and rule.disabled:
                continue
            route_match = match_route(rule.pattern, path)
            if route_match is not None:
                return rule, route_match
        return None

    @staticmethod
    def _redirect(
        rule: SystemRedirectRule,
        route_match: RouteMatch,
        request: FrontendRouteRequest,
    ) -> RedirectSettlement:
        location = rule.location_template
        if route_match.wildcard is not None:
            location = location.replace("*", route_match.wildcard)
            if request.query:
                location += "?" + urlencode(request.query)
        return RedirectSettlement(location=location, status_code=rule.status_code)

    @staticmethod
    def _app_settlement(
        rule: SystemAppRule,
        route_match: RouteMatch,
        path: str,
    ) -> AppSettlement:
        captures = route_match.captures
        seed = merge_seed(EmptySeed(), captures, rule.seed)
        route_data = {k: v for k, v in captures.items() if k not in CONTROL_NAMES}
        route_data.update(rule.route_data)

        locked_module = explicit_module(rule.seed)
        constraint = (
            ModuleRouteConstraint(module=locked_module)
            if locked_module is not None
            else AnyAppRouteConstraint()
        )

        if "url" in captures:
            remainder = captures["url"]
            matched_prefix = path[: len(path) - len(remainder)] if remainder else path
        elif route_match.wildcard is not None:
            remainder = route_match.wildcard
            matched_prefix = path[: len(path) - len(remainder)] if remainder else path
        else:
            matched_prefix = path

        remaining_path = path[len(matched_prefix):]

        return AppSettlement(
            app=rule.app,
            matched_prefix=matched_prefix,
            remaining_path=remaining_path,
            seed=seed,
            constraint=constraint,
            route_data=route_data,
        )
