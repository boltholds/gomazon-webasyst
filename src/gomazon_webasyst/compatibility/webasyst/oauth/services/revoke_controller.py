from gomazon_webasyst.application.oauth_authorization.vo.revoke import (
    OAuthRevokeTarget,
    RevokeTargetMissing,
    RevokeTargetProvided,
)
from gomazon_webasyst.compatibility.webasyst.oauth.composites.controller_response import (
    OAuthControllerPayloadResponse,
)
from gomazon_webasyst.contracts.api_credentials import (
    ApiAccessTokenAlreadyMissing,
    ApiAccessTokenRevoked,
)
from gomazon_webasyst.contracts.enums import ApiResponseFormat


class LegacyOAuthRevokeController:
    def __init__(self, revoke_api_access_token) -> None:
        self._revoke_api_access_token = revoke_api_access_token

    async def execute(
        self,
        target: OAuthRevokeTarget,
        response_format: ApiResponseFormat,
    ) -> OAuthControllerPayloadResponse:
        if isinstance(target, RevokeTargetMissing):
            return OAuthControllerPayloadResponse(
                status_code=200,
                payload={"access_token": ""},
                format=response_format,
            )

        if not isinstance(target, RevokeTargetProvided):
            raise AssertionError("unsupported revoke target")

        result = await self._revoke_api_access_token(target.token)
        if not isinstance(result, ApiAccessTokenRevoked | ApiAccessTokenAlreadyMissing):
            raise AssertionError("unsupported api access token revocation result")

        return OAuthControllerPayloadResponse(
            status_code=200,
            payload={"access_token": target.token.value},
            format=response_format,
        )
