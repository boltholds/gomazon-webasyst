from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias
from urllib.parse import unquote_to_bytes, urlencode

from gomazon_webasyst.contracts.routing import (
    AppSettlement,
    FrontendRouteRequest,
    RedirectSettlement,
    SettlementResolution,
)

from .errors import RouteNotFound
from .legacy_parser import SystemAppRule, SystemRedirectRule, SystemRouteRule, SystemRouteTable
from .patterns import (
    NoWildcard,
    RouteMatch,
    RouteMatched,
    RouteNotMatched,
    WildcardCapture,
    match_route,
)
from .seed_utils import CONTROL_NAMES, EmptySeed, app_route_constraint, merge_seed


@dataclass(frozen=True, slots=True)
class SystemRuleMatched:
    rule: SystemRouteRule
    route_match: RouteMatch


@dataclass(frozen=True, slots=True)
class SystemRuleNotMatched:
    pass


SystemRuleMatch: TypeAlias = SystemRuleMatched | SystemRuleNotMatched


class SystemRouteResolver:
    def __init__(self, table: SystemRouteTable):
        self._table = table

    def resolve(self, request: FrontendRouteRequest) -> SettlementResolution:
        path = self._decode_path(request.path)
        rules = (
            self._table.routes[request.domain]
            if request.domain in self._table.routes
            else self._table.routes.get("default", ())
        )

        first = self._match_once(rules, path)
        if isinstance(first, SystemRuleMatched) and isinstance(first.rule, SystemRedirectRule):
            return self._redirect(first.rule, first.route_match, request)

        retry = self._needs_trailing_slash_retry(first, path)
        if retry:
            second = self._match_once(rules, path + "/")
            if isinstance(second, SystemRuleMatched):
                if isinstance(second.rule, SystemRedirectRule):
                    return self._redirect(second.rule, second.route_match, request)
                if isinstance(first, SystemRuleNotMatched) or second.rule.pattern.source != "*":
                    return RedirectSettlement(location="/" + path + "/", status_code=301)

        if isinstance(first, SystemRuleNotMatched):
            raise RouteNotFound(f"no Webasyst settlement for {request.domain}/{path}")
        return self._app_settlement(first.rule, first.route_match, path)

    @staticmethod
    def _needs_trailing_slash_retry(first: SystemRuleMatch, path: str) -> bool:
        if isinstance(first, SystemRuleNotMatched):
            return not path.endswith("/")
        return (
            first.rule.pattern.source == "*"
            and bool(path)
            and "." not in path[-5:]
            and not path.endswith("/")
        )

    @staticmethod
    def _decode_path(path: str) -> str:
        try:
            return unquote_to_bytes(path).decode("utf-8")
        except UnicodeDecodeError:
            return path

    @staticmethod
    def _match_once(
        rules: tuple[SystemRouteRule, ...], path: str
    ) -> SystemRuleMatch:
        for rule in rules:
            if rule.temporarily_off:
                continue
            if isinstance(rule, SystemRedirectRule) and rule.disabled:
                continue
            pattern_result = match_route(rule.pattern, path)
            if isinstance(pattern_result, RouteMatched):
                return SystemRuleMatched(rule=rule, route_match=pattern_result.match)
            if not isinstance(pattern_result, RouteNotMatched):
                raise TypeError(f"unsupported route match result: {type(pattern_result)!r}")
        return SystemRuleNotMatched()

    @staticmethod
    def _redirect(
        rule: SystemRedirectRule,
        route_match: RouteMatch,
        request: FrontendRouteRequest,
    ) -> RedirectSettlement:
        location = rule.location_template
        if isinstance(route_match.wildcard, WildcardCapture):
            location = location.replace("*", route_match.wildcard.value)
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

        constraint = app_route_constraint(rule.seed)

        if "url" in captures:
            remainder = captures["url"]
            matched_prefix = path[: len(path) - len(remainder)] if remainder else path
        elif isinstance(route_match.wildcard, WildcardCapture):
            remainder = route_match.wildcard.value
            matched_prefix = path[: len(path) - len(remainder)] if remainder else path
        elif isinstance(route_match.wildcard, NoWildcard):
            matched_prefix = path
        else:
            raise TypeError(f"unsupported wildcard variant: {type(route_match.wildcard)!r}")

        remaining_path = path[len(matched_prefix):]

        return AppSettlement(
            app=rule.app,
            matched_prefix=matched_prefix,
            remaining_path=remaining_path,
            seed=seed,
            constraint=constraint,
            route_data=route_data,
        )
