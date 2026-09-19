from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.application.oauth_authorization.vo.authorization import (
    OAuthCsrfToken,
)


@dataclass(slots=True, frozen=True)
class LegacyOAuthCancelRequest:
    raw_response_type: str
    raw_redirect_uri: str
    raw_client_name: str


@dataclass(slots=True, frozen=True)
class OAuthRedirectLocation:
    location: str


@dataclass(slots=True, frozen=True)
class OAuthCsrfCookieMissing:
    pass


@dataclass(slots=True, frozen=True)
class OAuthCsrfCookieProvided:
    value: str


OAuthCsrfCookieState: TypeAlias = OAuthCsrfCookieMissing | OAuthCsrfCookieProvided


@dataclass(slots=True, frozen=True)
class OAuthCsrfFormMissing:
    pass


@dataclass(slots=True, frozen=True)
class OAuthCsrfFormProvided:
    value: str


OAuthCsrfFormState: TypeAlias = OAuthCsrfFormMissing | OAuthCsrfFormProvided


@dataclass(slots=True, frozen=True)
class OAuthCsrfIssued:
    token: OAuthCsrfToken
    set_cookie: bool


@dataclass(slots=True, frozen=True)
class OAuthCsrfAccepted:
    pass


@dataclass(slots=True, frozen=True)
class OAuthCsrfRejected:
    pass


OAuthCsrfValidation: TypeAlias = OAuthCsrfAccepted | OAuthCsrfRejected
