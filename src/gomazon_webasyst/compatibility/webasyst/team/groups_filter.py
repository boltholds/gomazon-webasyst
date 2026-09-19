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

    @staticmethod
    def _to_strings(value: ApiParameterValue) -> tuple[str, ...]:
        if isinstance(value, str):
            return (value,) if value else ()
        if isinstance(value, tuple):
            return tuple(
                item
                for item in value
                if isinstance(item, str) and item
            )
        if isinstance(value, int | float | bool):
            return (str(value),)
        return ()
