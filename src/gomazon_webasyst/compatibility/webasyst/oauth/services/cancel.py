from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.compatibility.webasyst.oauth.services.redirects import (
    LegacyOAuthRedirectService,
)
from gomazon_webasyst.compatibility.webasyst.oauth.vo.transport import (
    LegacyOAuthCancelRequest,
)
from gomazon_webasyst.application.oauth_authorization.vo.authorization import (
    OAuthRedirectUri,
)
from gomazon_webasyst.contracts.api_execution import ApiFrameworkError
from gomazon_webasyst.contracts.enums import ApiFrameworkErrorCode


@dataclass(slots=True, frozen=True)
class OAuthCancelRedirect:
    location: str


@dataclass(slots=True, frozen=True)
class OAuthCancelFrameworkError:
    error: ApiFrameworkError


OAuthCancelResult: TypeAlias = OAuthCancelRedirect | OAuthCancelFrameworkError


class LegacyOAuthCancelService:
    def cancel(self, request: LegacyOAuthCancelRequest) -> OAuthCancelResult:
        redirects = LegacyOAuthRedirectService()
        if request.raw_response_type == "token":
            return OAuthCancelRedirect(
                location=redirects.error_fragment_raw(
                    request.raw_redirect_uri
                ).location
            )

        if request.raw_redirect_uri not in {"", "0"}:
            return OAuthCancelRedirect(
                location=redirects.error_query(
                    OAuthRedirectUri(request.raw_redirect_uri)
                ).location
            )

        return OAuthCancelFrameworkError(
            error=ApiFrameworkError(
                code=ApiFrameworkErrorCode.ACCESS_DENIED,
                description=(
                    "User denied access"
                    if not request.raw_client_name
                    else f"User denied access for {request.raw_client_name}"
                ),
                http_status=403,
                details={},
            )
        )
