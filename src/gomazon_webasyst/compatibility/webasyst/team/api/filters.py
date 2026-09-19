from collections.abc import Mapping

from gomazon_webasyst.application.access_values import AppId, GroupId
from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiParameterMap,
)
from gomazon_webasyst.application.team_directory.vo.filters import (
    AllTeamUsers,
    TeamAppAccessRequirement,
    TeamGroupsFilter,
    TeamUsersFilter,
    TeamUsersInGroups,
)
from gomazon_webasyst.contracts.enums import GroupType, TeamAccessLevel


class LegacyTeamApiFilterParser:
    def users(self, query: ApiParameterMap) -> TeamUsersFilter:
        raw_filter = query["filter"] if "filter" in query else {}
        if not isinstance(raw_filter, Mapping):
            raw_filter = {}

        group_ids = self._positive_group_ids(
            raw_filter.get("group_id", ())
        )
        scope = (
            TeamUsersInGroups(group_ids)
            if group_ids
            else AllTeamUsers()
        )
        access = self._access_requirements(
            raw_filter.get("access", ())
        )
        return TeamUsersFilter(scope=scope, access=access)

    def groups(self, query: ApiParameterMap) -> TeamGroupsFilter:
        raw_filter = query["filter"] if "filter" in query else {}
        if not isinstance(raw_filter, Mapping):
            return TeamGroupsFilter(frozenset())
        raw_types = self._as_sequence(raw_filter.get("type", ()))
        types: set[GroupType] = set()
        for raw in raw_types:
            if raw == GroupType.GROUP.value:
                types.add(GroupType.GROUP)
            elif raw == GroupType.LOCATION.value:
                types.add(GroupType.LOCATION)
        return TeamGroupsFilter(frozenset(types))

    @staticmethod
    def _positive_group_ids(value: object) -> tuple[GroupId, ...]:
        result: list[GroupId] = []
        seen: set[int] = set()
        for raw in LegacyTeamApiFilterParser._as_sequence(value):
            try:
                parsed = int(raw)
            except (TypeError, ValueError):
                continue
            if parsed <= 0 or parsed in seen:
                continue
            seen.add(parsed)
            result.append(GroupId(parsed))
        return tuple(result)

    @staticmethod
    def _access_requirements(
        value: object,
    ) -> tuple[TeamAppAccessRequirement, ...]:
        normalized: dict[AppId, TeamAccessLevel] = {}
        if isinstance(value, Mapping):
            for raw_app_id, raw_level in value.items():
                if not isinstance(raw_app_id, str) or not raw_app_id:
                    continue
                if raw_level == TeamAccessLevel.LIMITED.value:
                    level = TeamAccessLevel.LIMITED
                elif raw_level == TeamAccessLevel.FULL.value:
                    level = TeamAccessLevel.FULL
                else:
                    continue
                try:
                    normalized[AppId(raw_app_id)] = level
                except ValueError:
                    continue
        else:
            for raw_app_id in LegacyTeamApiFilterParser._as_sequence(value):
                if not isinstance(raw_app_id, str) or not raw_app_id:
                    continue
                try:
                    normalized[AppId(raw_app_id)] = TeamAccessLevel.LIMITED
                except ValueError:
                    continue
        return tuple(
            TeamAppAccessRequirement(app_id, level)
            for app_id, level in normalized.items()
        )

    @staticmethod
    def _as_sequence(value: object) -> tuple[object, ...]:
        if isinstance(value, tuple):
            return value
        if isinstance(value, str):
            return (value,)
        return ()
