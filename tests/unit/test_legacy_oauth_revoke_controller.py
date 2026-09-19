import pytest

from gomazon_webasyst.application.api_credential_values import ApiAccessToken
from gomazon_webasyst.application.oauth_authorization.vo.revoke import (
    RevokeTargetMissing,
    RevokeTargetProvided,
)
from gomazon_webasyst.contracts.api_credentials import (
    ApiAccessTokenAlreadyMissing,
    ApiAccessTokenRevoked,
)
from gomazon_webasyst.contracts.enums import ApiResponseFormat


TOKEN = ApiAccessToken("a" * 32)


def _controller():
    from gomazon_webasyst.compatibility.webasyst.oauth.services.revoke_controller import (
        LegacyOAuthRevokeController,
    )
    return LegacyOAuthRevokeController


class Revoker:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def __call__(self, token):
        self.calls.append(token)
        return self.result


@pytest.mark.asyncio
async def test_header_only_target_missing_is_noop_and_returns_empty_token() -> None:
    Controller = _controller()
    revoker = Revoker(ApiAccessTokenRevoked(access_token=TOKEN))
    response = await Controller(revoker).execute(
        RevokeTargetMissing(),
        ApiResponseFormat.JSON,
    )
    assert response.status_code == 200
    assert response.payload == {"access_token": ""}
    assert revoker.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "result",
    [
        ApiAccessTokenRevoked(access_token=TOKEN),
        ApiAccessTokenAlreadyMissing(access_token=TOKEN),
    ],
)
async def test_provided_target_returns_same_value_for_revoked_or_missing(result) -> None:
    Controller = _controller()
    revoker = Revoker(result)
    response = await Controller(revoker).execute(
        RevokeTargetProvided(TOKEN),
        ApiResponseFormat.JSON,
    )
    assert response.payload == {"access_token": TOKEN.value}
    assert revoker.calls == [TOKEN]
