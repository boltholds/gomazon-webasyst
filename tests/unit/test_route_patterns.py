from gomazon_webasyst.compatibility.webasyst.routing.patterns import (
    compile_route_pattern,
    match_route,
)


def test_literal_and_named_capture() -> None:
    pattern = compile_route_pattern(r"post/<id:\d+>/")
    match = match_route(pattern, "post/42/")
    assert match is not None
    assert match.captures == {"id": "42"}


def test_default_capture_is_non_greedy() -> None:
    pattern = compile_route_pattern("tag/<slug>/")
    match = match_route(pattern, "tag/a-b/")
    assert match is not None
    assert match.captures == {"slug": "a-b"}


def test_wildcard_matches_remaining_path() -> None:
    pattern = compile_route_pattern("files/*")
    match = match_route(pattern, "files/a/b.txt")
    assert match is not None
    assert match.wildcard == "a/b.txt"


def test_match_is_case_insensitive_like_php_ui_regex() -> None:
    pattern = compile_route_pattern("Blog/<slug>/")
    assert match_route(pattern, "blog/Hello/") is not None


def test_literal_dot_is_not_regex_any_character() -> None:
    pattern = compile_route_pattern("feed.xml")
    assert match_route(pattern, "feed.xml") is not None
    assert match_route(pattern, "feedXxml") is None


def test_parentheses_become_non_capturing_group_like_legacy() -> None:
    pattern = compile_route_pattern("archive/(old|new)/")
    assert match_route(pattern, "archive/old/") is not None
    assert match_route(pattern, "archive/new/") is not None
