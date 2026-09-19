from gomazon_webasyst.application.access_values import AppId, GroupId
from gomazon_webasyst.application.api_execution.vo.parameters import ApiParameterMap
from gomazon_webasyst.application.team_directory.vo.filters import (
    AllTeamUsers,
    TeamUsersInGroups,
)
from gomazon_webasyst.compatibility.webasyst.team.api.filters import (
    LegacyTeamApiFilterParser,
)
from gomazon_webasyst.contracts.enums import GroupType, TeamAccessLevel


def test_users_filter_parses_group_ids_and_drops_invalid_or_duplicate_values() -> None:
    filters = LegacyTeamApiFilterParser().users(
        ApiParameterMap(
            {
                "filter": {
                    "group_id": ("7", "0", "-2", "oops", "7", "9")
                }
            }
        )
    )
    assert isinstance(filters.scope, TeamUsersInGroups)
    assert filters.scope.group_ids == (GroupId(7), GroupId(9))


def test_users_filter_without_positive_group_ids_is_explicit_all_users() -> None:
    filters = LegacyTeamApiFilterParser().users(
        ApiParameterMap({"filter": {"group_id": ("0", "-1")}})
    )
    assert isinstance(filters.scope, AllTeamUsers)


def test_access_list_defaults_each_app_to_limited_and_dedupes_last() -> None:
    filters = LegacyTeamApiFilterParser().users(
        ApiParameterMap(
            {"filter": {"access": ("crm", "", "files", "crm")}}
        )
    )
    assert tuple(
        (item.app_id, item.level) for item in filters.access
    ) == (
        (AppId("crm"), TeamAccessLevel.LIMITED),
        (AppId("files"), TeamAccessLevel.LIMITED),
    )


def test_access_mapping_accepts_only_limited_and_full() -> None:
    filters = LegacyTeamApiFilterParser().users(
        ApiParameterMap(
            {
                "filter": {
                    "access": {
                        "crm": "limited",
                        "files": "full",
                        "bad": "admin",
                    }
                }
            }
        )
    )
    assert tuple(
        (item.app_id.value, item.level.value)
        for item in filters.access
    ) == (
        ("crm", "limited"),
        ("files", "full"),
    )


def test_groups_type_filter_ignores_unknown_types() -> None:
    filters = LegacyTeamApiFilterParser().groups(
        ApiParameterMap(
            {"filter": {"type": ("group", "unknown", "location")}}
        )
    )
    assert filters.types == frozenset(
        {GroupType.GROUP, GroupType.LOCATION}
    )


def test_explicit_numeric_php_array_indexes_are_treated_as_list_values() -> None:
    parser = LegacyTeamApiFilterParser()
    users = parser.users(
        ApiParameterMap(
            {
                "filter": {
                    "group_id": {"0": "7", "1": "9"},
                    "access": {"0": "crm", "1": "files"},
                }
            }
        )
    )
    groups = parser.groups(
        ApiParameterMap(
            {
                "filter": {
                    "type": {"0": "group", "1": "location"}
                }
            }
        )
    )

    assert users.scope.group_ids == (GroupId(7), GroupId(9))
    assert tuple(item.app_id.value for item in users.access) == (
        "crm",
        "files",
    )
    assert all(
        item.level is TeamAccessLevel.LIMITED
        for item in users.access
    )
    assert groups.types == frozenset(
        {GroupType.GROUP, GroupType.LOCATION}
    )
