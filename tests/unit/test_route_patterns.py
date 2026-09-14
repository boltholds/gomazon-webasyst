from gomazon_webasyst.compatibility.webasyst.routing.patterns import (
    RouteMatched,
    RouteNotMatched,
    WildcardCapture,
    compile_route_pattern,
    match_route,
)


def test_literal_and_named_capture() -> None:
    pattern = compile_route_pattern(r"post/<id:\d+>/")
    result = match_route(pattern, "post/42/")
    assert isinstance(result, RouteMatched)
    assert result.match.captures == {"id": "42"}


def test_default_capture_is_non_greedy() -> None:
    pattern = compile_route_pattern("tag/<slug>/")
    result = match_route(pattern, "tag/a-b/")
    assert isinstance(result, RouteMatched)
    assert result.match.captures == {"slug": "a-b"}


def test_wildcard_matches_remaining_path() -> None:
    pattern = compile_route_pattern("files/*")
    result = match_route(pattern, "files/a/b.txt")
    assert isinstance(result, RouteMatched)
    assert result.match.wildcard == WildcardCapture("a/b.txt")


def test_match_is_case_insensitive_like_php_ui_regex() -> None:
    pattern = compile_route_pattern("Blog/<slug>/")
    assert isinstance(match_route(pattern, "blog/Hello/"), RouteMatched)


def test_literal_dot_is_not_regex_any_character() -> None:
    pattern = compile_route_pattern("feed.xml")
    assert isinstance(match_route(pattern, "feed.xml"), RouteMatched)
    assert isinstance(match_route(pattern, "feedXxml"), RouteNotMatched)


def test_parentheses_become_non_capturing_group_like_legacy() -> None:
    pattern = compile_route_pattern("archive/(old|new)/")
    assert isinstance(match_route(pattern, "archive/old/"), RouteMatched)
    assert isinstance(match_route(pattern, "archive/new/"), RouteMatched)
