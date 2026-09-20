import re
from collections.abc import Mapping

from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiParameterValue,
    ApiRequestParameters,
)
from gomazon_webasyst.contracts.enums import TeamUserAccessLevel
from gomazon_webasyst.contracts.team import (
    TeamUserAccessRequirement,
    TeamUserFilter,
)


_ACCESS_KEY = re.compile(r"^filter\[access\]\[([^\]]+)\]$")


class LegacyTeamUserFilterParser:
    def parse(self, parameters: ApiRequestParameters) -> TeamUserFilter:
        query = parameters.query.values
        nested = query.get("filter")
        if isinstance(nested, Mapping):
            return TeamUserFilter(
                group_ids=self._group_ids(nested.get("group_id", ())),
                access=self._access(nested.get("access", ())),
            )

        group_value: ApiParameterValue = ()
        for key in ("filter[group_id][]", "filter[group_id]"):
            if key in query:
                group_value = query[key]
                break

        access_by_app: dict[str, TeamUserAccessLevel] = {}
        for key, value in query.items():
            match = _ACCESS_KEY.match(key)
            if not match or not match.group(1):
                continue
            app_id = match.group(1).strip()
            if not app_id:
                continue
            level = self._access_level(value)
            if level is not None:
                access_by_app[app_id] = level

        if not access_by_app:
            for key in ("filter[access][]", "filter[access]"):
                if key in query:
                    access_by_app = {
                        item: TeamUserAccessLevel.LIMITED
                        for item in self._strings(query[key])
                        if item
                    }
                    break

        return TeamUserFilter(
            group_ids=self._group_ids(group_value),
            access=tuple(
                TeamUserAccessRequirement(app_id=app_id, level=level)
                for app_id, level in access_by_app.items()
            ),
        )

    def _access(
        self,
        value: ApiParameterValue,
    ) -> tuple[TeamUserAccessRequirement, ...]:
        if isinstance(value, Mapping):
            result: list[TeamUserAccessRequirement] = []
            for app_id, raw_level in value.items():
                normalized_app_id = str(app_id).strip()
                if not normalized_app_id:
                    continue
                level = self._access_level(raw_level)
                if level is None:
                    continue
                result.append(
                    TeamUserAccessRequirement(
                        app_id=normalized_app_id,
                        level=level,
                    )
                )
            return tuple(result)
        return tuple(
            TeamUserAccessRequirement(
                app_id=app_id,
                level=TeamUserAccessLevel.LIMITED,
            )
            for app_id in dict.fromkeys(self._strings(value))
            if app_id
        )

    @staticmethod
    def _access_level(
        value: ApiParameterValue,
    ) -> TeamUserAccessLevel | None:
        if isinstance(value, Mapping | tuple):
            return None
        normalized = str(value).strip()
        if normalized == TeamUserAccessLevel.LIMITED.value:
            return TeamUserAccessLevel.LIMITED
        if normalized == TeamUserAccessLevel.FULL.value:
            return TeamUserAccessLevel.FULL
        return None

    @classmethod
    def _group_ids(cls, value: ApiParameterValue) -> tuple[int, ...]:
        result: list[int] = []
        for raw in cls._values(value):
            candidate = cls._positive_int(raw)
            if candidate is None or candidate in result:
                continue
            result.append(candidate)
        return tuple(result)

    @classmethod
    def _strings(cls, value: ApiParameterValue) -> tuple[str, ...]:
        return tuple(
            str(item).strip()
            for item in cls._values(value)
            if str(item).strip()
        )

    @staticmethod
    def _values(value: ApiParameterValue) -> tuple[ApiParameterValue, ...]:
        if isinstance(value, tuple):
            return value
        if isinstance(value, Mapping):
            return ()
        return (value,)

    @staticmethod
    def _positive_int(value: ApiParameterValue) -> int | None:
        if isinstance(value, Mapping | tuple):
            return None
        if isinstance(value, bool):
            candidate = int(value)
        elif isinstance(value, int | float):
            candidate = int(value)
        else:
            match = re.match(r"^[\s]*([+-]?\d+)", str(value))
            if match is None:
                return None
            candidate = int(match.group(1))
        return candidate if candidate > 0 else None
