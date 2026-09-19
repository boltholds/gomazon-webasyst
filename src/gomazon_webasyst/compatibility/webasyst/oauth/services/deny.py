from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.application.oauth_authorization.composites.requests import (
    OAuthAuthorizationRequest,
)
from gomazon_webasyst.application.oauth_authorization.vo.authorization import (
    OAuthRedirectMissing,
    OAuthRedirectProvided,
)
from gomazon_webasyst.compatibility.webasyst.oauth.services.redirects import (
    LegacyOAuthRedirectService,
)
from gomazon_webasyst.contracts.enums import OAuthResponseType


@dataclass(slots=True, frozen=True)
class OAuthDenyRedirect:
    location: str


@dataclass(slots=True, frozen=True)
class OAuthDenyHtmlError:
    error_code: str
    description: str


OAuthDenyResult: TypeAlias = OAuthDenyRedirect | OAuthDenyHtmlError


class LegacyOAuthDenyService:
    def deny(self, request: OAuthAuthorizationRequest) -> OAuthDenyResult:
        redirects = LegacyOAuthRedirectService()
        target = request.redirect_target

        if request.response_type is OAuthResponseType.TOKEN:
            if not isinstance(target, OAuthRedirectProvided):
                raise AssertionError("token response requires redirect")
            return OAuthDenyRedirect(
                location=redirects.error_fragment(target.uri).location
            )

        if request.response_type is OAuthResponseType.CODE:
            if isinstance(target, OAuthRedirectProvided):
                return OAuthDenyRedirect(
                    location=redirects.error_query(target.uri).location
                )
            if isinstance(target, OAuthRedirectMissing):
                return OAuthDenyHtmlError(
                    error_code="access_denied",
                    description=(
                        f"Access to API revoked for {request.client_name.value}"
                    ),
                )

        raise AssertionError("unsupported oauth denial request")
