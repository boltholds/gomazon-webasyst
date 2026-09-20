from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiParameterMap,
    ApiRequestParameters,
)
from gomazon_webasyst.compatibility.webasyst.team.users_filter import (
    LegacyTeamUserFilterParser,
)
from gomazon_webasyst.contracts.enums import TeamUserAccessLevel


def _parameters(query) -> ApiRequestParameters:
    return ApiRequestParameters(
        query=ApiParameterMap(query),
        form=ApiParameterMap({}),
    )


def test_flat_repeated_group_and_access_filters_are_normalized() -> None:
    parsed = LegacyTeamUserFilterParser().parse(
        _parameters(
            {
                "filter[group_id][]": ("2", "0", "3junk", "-4", "2"),
                "filter[access][]": ("crm", "files", "crm"),
            }
        )
    )

    assert parsed.group_ids == (2, 3)
    assert [(item.app_id, item.level) for item in parsed.access] == [
        ("crm", TeamUserAccessLevel.LIMITED),
        ("files", TeamUserAccessLevel.LIMITED),
    ]


def test_nested_associative_access_keeps_only_known_levels() -> None:
    parsed = LegacyTeamUserFilterParser().parse(
        _parameters(
            {
                "filter": {
                    "group_id": ("5", "6"),
                    "access": {
                        "crm": "limited",
                        "files": "full",
                        "bad": "owner",
                    },
                }
            }
        )
    )

    assert parsed.group_ids == (5, 6)
    assert [(item.app_id, item.level) for item in parsed.access] == [
        ("crm", TeamUserAccessLevel.LIMITED),
        ("files", TeamUserAccessLevel.FULL),
    ]


def test_flat_associative_access_is_supported() -> None:
    parsed = LegacyTeamUserFilterParser().parse(
        _parameters(
            {
                "filter[access][crm]": "limited",
                "filter[access][files]": "full",
                "filter[access][bad]": "invalid",
            }
        )
    )

    assert [(item.app_id, item.level) for item in parsed.access] == [
        ("crm", TeamUserAccessLevel.LIMITED),
        ("files", TeamUserAccessLevel.FULL),
    ]
