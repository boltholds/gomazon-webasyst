from gomazon_webasyst.application.api_execution.composites.invocation import (
    ApiInvocationContext,
)
from gomazon_webasyst.application.api_execution.composites.results import (
    ApiMethodSucceeded,
)
from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiRequestParameters,
)
from gomazon_webasyst.application.team.groups import ListVisibleTeamGroups
from gomazon_webasyst.compatibility.webasyst.team.groups_filter import (
    LegacyTeamGroupFilterParser,
)


class TeamGroupsGetListApiMethod:
    def __init__(
        self,
        *,
        list_groups: ListVisibleTeamGroups,
        filter_parser: LegacyTeamGroupFilterParser,
    ) -> None:
        self._list_groups = list_groups
        self._filter_parser = filter_parser

    async def execute(
        self,
        context: ApiInvocationContext,
        parameters: ApiRequestParameters,
    ) -> ApiMethodSucceeded:
        group_filter = self._filter_parser.parse(parameters)
        groups = await self._list_groups.execute(
            contact_id=context.principal.contact_id,
            group_filter=group_filter,
        )
        return ApiMethodSucceeded(
            payload=[
                group.model_dump(mode="json")
                for group in groups
            ]
        )
