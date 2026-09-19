from gomazon_webasyst.application.api_execution.composites.invocation import (
    ApiInvocationContext,
)
from gomazon_webasyst.application.api_execution.composites.results import (
    ApiMethodResult,
    ApiMethodSucceeded,
)
from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiRequestParameters,
)
from gomazon_webasyst.application.ports.api_methods import ApiMethodHandler
from gomazon_webasyst.application.team_directory.composites.list_groups import (
    ListTeamGroups,
)
from gomazon_webasyst.application.team_directory.composites.list_users import (
    ListTeamUsers,
)
from gomazon_webasyst.compatibility.webasyst.team.api.filters import (
    LegacyTeamApiFilterParser,
)
from gomazon_webasyst.compatibility.webasyst.team.api.projection import (
    LegacyTeamApiProjector,
)


class TeamUsersGetListApiMethod(ApiMethodHandler):
    def __init__(
        self,
        *,
        list_users: ListTeamUsers,
        filters: LegacyTeamApiFilterParser,
        projector: LegacyTeamApiProjector,
    ) -> None:
        self._list_users = list_users
        self._filters = filters
        self._projector = projector

    async def execute(
        self,
        context: ApiInvocationContext,
        parameters: ApiRequestParameters,
    ) -> ApiMethodResult:
        filters = self._filters.users(parameters.query)
        result = await self._list_users(
            context.principal.contact_id,
            filters,
        )
        return ApiMethodSucceeded(
            payload=[
                self._projector.user(user, context.origin)
                for user in result.users
            ],
            status_code=200,
        )


class TeamGroupsGetListApiMethod(ApiMethodHandler):
    def __init__(
        self,
        *,
        list_groups: ListTeamGroups,
        filters: LegacyTeamApiFilterParser,
        projector: LegacyTeamApiProjector,
    ) -> None:
        self._list_groups = list_groups
        self._filters = filters
        self._projector = projector

    async def execute(
        self,
        context: ApiInvocationContext,
        parameters: ApiRequestParameters,
    ) -> ApiMethodResult:
        filters = self._filters.groups(parameters.query)
        result = await self._list_groups(
            context.principal.contact_id,
            filters,
        )
        return ApiMethodSucceeded(
            payload=[
                self._projector.group(group)
                for group in result.groups
            ],
            status_code=200,
        )
