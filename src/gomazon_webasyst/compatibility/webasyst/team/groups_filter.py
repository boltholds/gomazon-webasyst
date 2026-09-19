from collections.abc import Mapping

from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiParameterValue,
    ApiRequestParameters,
)
from gomazon_webasyst.contracts.team import TeamGroupFilter


class LegacyTeamGroupFilterParser:
    def parse(self, parameters: ApiRequestParameters) -> TeamGroupFilter:
        query = parameters.query.values

        nested = query.get("filter")
        if isinstance(nested, Mapping) and "type" in nested:
            return TeamGroupFilter(types=self._to_strings(nested["type"]))

        for key in ("filter[type][]", "filter[type]"):
            if key in query:
                return TeamGroupFilter(types=self._to_strings(query[key]))

        return TeamGroupFilter()

    @classmethod
    def _to_strings(
        cls,
        value: ApiParameterValue,
    ) -> tuple[str, ...]:
        if isinstance(value, tuple):
            return tuple(cls._scalar_string(item) for item in value)
        if isinstance(value, Mapping):
            return ()
        return (cls._scalar_string(value),)

    @staticmethod
    def _scalar_string(value: ApiParameterValue) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, bool):
            return "1" if value else ""
        if isinstance(value, int | float):
            return str(value)
        return ""
