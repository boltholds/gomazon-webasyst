from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from gomazon_webasyst.application.api_credential_values import (
    ApiAccessToken,
    ApiScope,
    AuthorizationCode,
)
from gomazon_webasyst.application.oauth_authorization.entities.consent_application import (
    OAuthConsentApplication,
)
from gomazon_webasyst.application.oauth_authorization.vo.authorization import (
    OAuthRedirectTarget,
)
from gomazon_webasyst.application.oauth_authorization.vo.client import OAuthClientName
from gomazon_webasyst.contracts.enums import (
    OAuthAuthorizationResultKind,
    OAuthResponseType,
)


class OAuthConsentRequired(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[OAuthAuthorizationResultKind.CONSENT_REQUIRED] = (
        OAuthAuthorizationResultKind.CONSENT_REQUIRED
    )
    client_name: OAuthClientName
    effective_scope: ApiScope
    applications: tuple[OAuthConsentApplication, ...]


class OAuthAuthorizationCodeGranted(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[OAuthAuthorizationResultKind.CODE_GRANTED] = (
        OAuthAuthorizationResultKind.CODE_GRANTED
    )
    code: AuthorizationCode
    redirect_target: OAuthRedirectTarget


class OAuthImplicitTokenGranted(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[OAuthAuthorizationResultKind.TOKEN_GRANTED] = (
        OAuthAuthorizationResultKind.TOKEN_GRANTED
    )
    access_token: ApiAccessToken
    redirect_target: OAuthRedirectTarget


class OAuthAuthorizationDenied(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    kind: Literal[OAuthAuthorizationResultKind.DENIED] = (
        OAuthAuthorizationResultKind.DENIED
    )
    response_type: OAuthResponseType
    redirect_target: OAuthRedirectTarget
    client_name: OAuthClientName


class OAuthAuthorizationInvalidScope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[OAuthAuthorizationResultKind.INVALID_SCOPE] = (
        OAuthAuthorizationResultKind.INVALID_SCOPE
    )


class OAuthAuthorizationGrantUnavailable(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[OAuthAuthorizationResultKind.GRANT_UNAVAILABLE] = (
        OAuthAuthorizationResultKind.GRANT_UNAVAILABLE
    )


OAuthAuthorizationResult: TypeAlias = Annotated[
    OAuthConsentRequired
    | OAuthAuthorizationCodeGranted
    | OAuthImplicitTokenGranted
    | OAuthAuthorizationDenied
    | OAuthAuthorizationInvalidScope
    | OAuthAuthorizationGrantUnavailable,
    Field(discriminator="kind"),
]
