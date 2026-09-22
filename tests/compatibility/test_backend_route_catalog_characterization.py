from pathlib import Path


RELEASE_SHA = "39c267a2fabfb0cd6d94f4dd86b23b4750328dd5"
ROOT = Path(__file__).resolve().parents[2]
FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "webasyst_4_2"
    / "team"
    / "routing_backend.txt"
)
CHARACTERIZATION = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-09-22-backend-route-catalog-characterization.md"
)


def test_backend_route_catalog_characterization_is_release_pinned() -> None:
    fixture = FIXTURE.read_text(encoding="utf-8")
    document = CHARACTERIZATION.read_text(encoding="utf-8")
    assert f"SOURCE_COMMIT: {RELEASE_SHA}" in fixture
    assert RELEASE_SHA in document


def test_team_backend_route_table_and_gate_are_pinned() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    for expected in (
        "1 = u/<login>/<tab>/? -> profile/",
        "20 = calendar/external/authorize/ -> explicit route mapping",
        "21 = empty -> users/",
        "module = calendarExternal",
        "action = authorize",
        "route_data.authorize_end = 1",
        "routing_backend_runs_only_when_query_module_is_php_empty = true",
        "routing_backend_runs_only_when_query_plugin_is_php_empty = true",
        "route_module_without_action_keeps_query_action = true",
        "route_miss_without_module_raises_dispatch_miss = true",
        "missing_routing_backend_file_uses_normal_backend_defaults = true",
    ):
        assert expected in text
