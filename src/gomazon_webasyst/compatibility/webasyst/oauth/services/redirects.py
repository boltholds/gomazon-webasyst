from gomazon_webasyst.application.api_credential_values import (
    ApiClientId,
    AuthorizationCode,
)
from gomazon_webasyst.application.oauth_authorization.vo.authorization import (
    OAuthRedirectTarget,
    OAuthRedirectUri,
)
from gomazon_webasyst.application.ports.oauth_redirect_policy import (
    OAuthRedirectAccepted,
    OAuthRedirectDecision,
)
from gomazon_webasyst.compatibility.webasyst.oauth.vo.transport import (
    OAuthRedirectLocation,
)


class LegacyUnregisteredRedirectPolicy:
    def validate(
        self,
        client_id: ApiClientId,
        redirect_target: OAuthRedirectTarget,
    ) -> OAuthRedirectDecision:
        return OAuthRedirectAccepted(redirect_target)


class LegacyOAuthRedirectService:
    @staticmethod
    def code(
        uri: OAuthRedirectUri,
        code: AuthorizationCode,
    ) -> OAuthRedirectLocation:
        separator = "&" if "?" in uri.value else "?"
        return OAuthRedirectLocation(
            f"{uri.value}{separator}code={code.value}"
        )

    @staticmethod
    def error_query(uri: OAuthRedirectUri) -> OAuthRedirectLocation:
        separator = "&" if "?" in uri.value else "?"
        return OAuthRedirectLocation(
            f"{uri.value}{separator}error=access_denied"
        )

    @staticmethod
    def error_fragment(uri: OAuthRedirectUri) -> OAuthRedirectLocation:
        return OAuthRedirectLocation(
            f"{uri.value}#error=access_denied"
        )

    @staticmethod
    def error_fragment_raw(raw_uri: str) -> OAuthRedirectLocation:
        return OAuthRedirectLocation(
            f"{raw_uri}#error=access_denied"
        )

    @staticmethod
    def token(uri: OAuthRedirectUri, token_value: str) -> OAuthRedirectLocation:
        return OAuthRedirectLocation(
            f"{uri.value}#access_token={token_value}"
        )
