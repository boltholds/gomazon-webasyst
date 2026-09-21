from datetime import datetime

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
    TeamUsersInviteApiMethod,
)
from gomazon_webasyst.compatibility.webasyst.team.invitation import (
    LegacyTeamInvitationRequestParser,
)
from gomazon_webasyst.contracts.team_invitation import (
    TeamInvitationEmailAccepted,
    TeamInvitationLinkCreated,
)


class FakeInviteUser:
    def __init__(self, result) -> None:
        self.result = result

    async def execute(self, *, actor_contact_id, request):
        del actor_contact_id, request
        return self.result


def _context() -> ApiInvocationContext:
    return ApiInvocationContext(
        principal=ApiPrincipalContext(
            contact_id=42,
            client_id=ApiClientId("client"),
            scope=ApiScope.of("team"),
        ),
        target=ApiMethodTarget(
            AppId("team"),
            ApiMethodName("users.invite"),
        ),
    )


def _parameters(*, send: str = "false") -> ApiRequestParameters:
    return ApiRequestParameters(
        query=ApiParameterMap({}),
        form=ApiParameterMap(
            {
                "email": "a@example.test",
                "send": send,
            }
        ),
    )


async def test_link_expire_uses_api_response_clock_not_token_expiry() -> None:
    method = TeamUsersInviteApiMethod(
        invite_user=FakeInviteUser(
            TeamInvitationLinkCreated(
                contact_id=7,
                invitation_link="https://example.test/link.php/token/",
            )
        ),
        request_parser=LegacyTeamInvitationRequestParser(),
        clock=lambda: 1_700_000_123,
    )

    result = await method.execute(_context(), _parameters())

    assert result.payload["invitation_expire"] == 1_700_259_323


async def test_sent_email_expire_uses_api_response_clock() -> None:
    method = TeamUsersInviteApiMethod(
        invite_user=FakeInviteUser(
            TeamInvitationEmailAccepted(contact_id=7)
        ),
        request_parser=LegacyTeamInvitationRequestParser(),
        clock=lambda: 1_700_000_999,
    )

    result = await method.execute(_context(), _parameters(send="true"))

    assert result.payload == {
        "contact_id": 7,
        "invitation_expire": 1_700_260_199,
    }
