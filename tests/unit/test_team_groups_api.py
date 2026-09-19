from gomazon_webasyst.application.access_values import AppId
from gomazon_webasyst.application.api_credential_values import ApiClientId, ApiScope
from gomazon_webasyst.application.api_execution.composites.invocation import (
    ApiInvocationContext,
    ApiPrincipalContext,
)
from gomazon_webasyst.application.api_execution.vo.method import (
    ApiMethodName,
    ApiMethodTarget,
)
from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiParameterMap,
    ApiRequestParameters,
)
from gomazon_webasyst.compatibility.webasyst.team.api import (
    TeamGroupsGetListApiMethod,
)
from gomazon_webasyst.compatibility.webasyst.team.groups_filter import (
    LegacyTeamGroupFilterParser,
)
from gomazon_webasyst.contracts.team import (
    TeamGroupDescriptionMissing,
    TeamGroupDescriptionPresent,
    TeamGroupRead,
)


class FakeListGroups:
    def __init__(self) -> None:
        self.calls = []

    async def execute(self, *, contact_id, group_filter):
        self.calls.append((contact_id, group_filter))
        return (
            TeamGroupRead(
                id=2,
                name="Office",
                cnt=3,
                type="location",
                description=TeamGroupDescriptionMissing(),
            ),
            TeamGroupRead(
                id=1,
                name="Engineering",
                cnt=5,
                type="group",
                description=TeamGroupDescriptionPresent(value="Developers"),
            ),
        )


async def test_team_groups_api_method_projects_exact_legacy_shape() -> None:
    service = FakeListGroups()
    method = TeamGroupsGetListApiMethod(
        list_groups=service,
        filter_parser=LegacyTeamGroupFilterParser(),
    )
    context = ApiInvocationContext(
        principal=ApiPrincipalContext(
            contact_id=42,
            client_id=ApiClientId("client"),
            scope=ApiScope.of("team"),
        ),
        target=ApiMethodTarget(
            AppId("team"),
            ApiMethodName("groups.getList"),
        ),
    )
    parameters = ApiRequestParameters(
        query=ApiParameterMap({"filter[type]": "group"}),
        form=ApiParameterMap({}),
    )

    result = await method.execute(context, parameters)

    assert service.calls[0][0] == 42
    assert service.calls[0][1].types == ("group",)
    assert result.payload == [
        {
            "id": 2,
            "name": "Office",
            "cnt": 3,
            "type": "location",
            "description": None,
        },
        {
            "id": 1,
            "name": "Engineering",
            "cnt": 5,
            "type": "group",
            "description": "Developers",
        },
    ]
