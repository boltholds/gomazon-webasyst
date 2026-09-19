from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiParameterMap,
    ApiRequestParameters,
)
from gomazon_webasyst.compatibility.webasyst.team.groups_filter import (
    LegacyTeamGroupFilterParser,
)


def _params(query) -> ApiRequestParameters:
    return ApiRequestParameters(
        query=ApiParameterMap(query),
        form=ApiParameterMap({}),
    )


def test_missing_filter_means_all_group_types() -> None:
    assert LegacyTeamGroupFilterParser().parse(_params({})).types == ()


def test_php_bracket_scalar_type_filter_is_supported() -> None:
    parsed = LegacyTeamGroupFilterParser().parse(
        _params({"filter[type]": "group"})
    )
    assert parsed.types == ("group",)


def test_php_bracket_list_type_filter_is_supported_when_transport_preserves_tuple() -> None:
    parsed = LegacyTeamGroupFilterParser().parse(
        _params({"filter[type][]": ("group", "location")})
    )
    assert parsed.types == ("group", "location")


def test_nested_filter_shape_is_supported_for_future_generic_php_query_parser() -> None:
    parsed = LegacyTeamGroupFilterParser().parse(
        _params({"filter": {"type": ("location", "group")}})
    )
    assert parsed.types == ("location", "group")
