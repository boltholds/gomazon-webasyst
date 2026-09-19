from collections.abc import Mapping

from gomazon_webasyst.application.api_credential_values import ApiAccessToken
from gomazon_webasyst.application.api_execution.vo.parameters import (
    ApiParameterMap,
    ApiParameterValue,
)
from gomazon_webasyst.application.oauth_authorization.vo.revoke import (
    OAuthRevokeTarget,
    RevokeTargetMissing,
    RevokeTargetProvided,
)


def _php_falsy(value: ApiParameterValue) -> bool:
    if value is False or value == 0 or value == 0.0:
        return True
    if isinstance(value, str):
        return value in {"", "0"}
    if isinstance(value, tuple | Mapping):
        return len(value) == 0
    return False


class LegacyRevokeTargetExtractor:
    def extract(
        self,
        *,
        query: ApiParameterMap,
        form: ApiParameterMap,
    ) -> OAuthRevokeTarget:
        if "access_token" in form:
            selected = form["access_token"]
        elif "access_token" in query:
            selected = query["access_token"]
        else:
            return RevokeTargetMissing()

        if _php_falsy(selected):
            return RevokeTargetMissing()
        return RevokeTargetProvided(ApiAccessToken(str(selected)))
