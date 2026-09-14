from dataclasses import dataclass
import re
from typing import TypeAlias

from gomazon_webasyst.contracts.routing import RouteCapture, RoutePattern


_PLACEHOLDER = re.compile(r"<([a-z_]+):?([^>]*)?>", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class NoWildcard:
    pass


@dataclass(frozen=True, slots=True)
class WildcardCapture:
    value: str


RouteWildcard: TypeAlias = NoWildcard | WildcardCapture


@dataclass(frozen=True, slots=True)
class RouteMatch:
    captures: dict[str, str]
    wildcard: RouteWildcard


@dataclass(frozen=True, slots=True)
class RouteMatched:
    match: RouteMatch


@dataclass(frozen=True, slots=True)
class RouteNotMatched:
    pass


RoutePatternMatch: TypeAlias = RouteMatched | RouteNotMatched


def _translate_literal(segment: str, wildcard_index: int) -> tuple[str, int]:
    out: list[str] = []
    i = 0
    while i < len(segment):
        char = segment[i]
        if char == " ":
            out.append(r"\s")
        elif char == ".":
            out.append(r"\.")
        elif char == "(":
            out.append("(?:")
        elif char == "!":
            out.append(r"\!")
        elif char == "*":
            while i + 1 < len(segment) and segment[i + 1] == "*":
                i += 1
            out.append(f"(?P<__wildcard_{wildcard_index}>.*?)")
            wildcard_index += 1
        else:
            out.append(char)
        i += 1
    return "".join(out), wildcard_index


def compile_route_pattern(source: str) -> RoutePattern:
    parts: list[str] = []
    captures: list[RouteCapture] = []
    cursor = 0
    wildcard_index = 0

    for match in _PLACEHOLDER.finditer(source):
        literal, wildcard_index = _translate_literal(source[cursor : match.start()], wildcard_index)
        parts.append(literal)
        name = match.group(1)
        capture_regex = match.group(2) or ".*?"
        captures.append(RouteCapture(name=name, regex=capture_regex))
        parts.append(f"(?P<{name}>{capture_regex})")
        cursor = match.end()

    literal, wildcard_index = _translate_literal(source[cursor:], wildcard_index)
    parts.append(literal)

    return RoutePattern(
        source=source,
        regex_source="".join(parts),
        captures=tuple(captures),
    )


def match_route(pattern: RoutePattern, path: str) -> RoutePatternMatch:
    regex_match = re.fullmatch(pattern.regex_source, path, flags=re.IGNORECASE)
    if regex_match is None:
        return RouteNotMatched()

    groups = regex_match.groupdict()
    captures = {capture.name: groups[capture.name] for capture in pattern.captures}
    wildcard_groups = [
        (name, value)
        for name, value in groups.items()
        if name.startswith("__wildcard_") and value is not None
    ]
    wildcard_groups.sort(key=lambda item: int(item[0].rsplit("_", 1)[1]))
    wildcard: RouteWildcard = (
        WildcardCapture(wildcard_groups[0][1]) if wildcard_groups else NoWildcard()
    )
    return RouteMatched(match=RouteMatch(captures=captures, wildcard=wildcard))
