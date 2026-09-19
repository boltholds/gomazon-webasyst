import secrets
from collections.abc import Callable

from gomazon_webasyst.application.oauth_authorization.vo.authorization import (
    OAuthCsrfToken,
)
from gomazon_webasyst.compatibility.webasyst.oauth.vo.transport import (
    OAuthCsrfAccepted,
    OAuthCsrfCookieMissing,
    OAuthCsrfCookieProvided,
    OAuthCsrfCookieState,
    OAuthCsrfFormMissing,
    OAuthCsrfFormProvided,
    OAuthCsrfFormState,
    OAuthCsrfIssued,
    OAuthCsrfRejected,
    OAuthCsrfValidation,
)


def _default_generator() -> str:
    return secrets.token_hex(16)


def _usable(value: str) -> bool:
    return value not in {"", "0"}


class LegacyOAuthCsrfService:
    def __init__(
        self,
        generator: Callable[[], str] = _default_generator,
    ) -> None:
        self._generator = generator

    def issue(
        self,
        cookie: OAuthCsrfCookieState,
    ) -> OAuthCsrfIssued:
        if isinstance(cookie, OAuthCsrfCookieProvided) and _usable(cookie.value):
            return OAuthCsrfIssued(
                token=OAuthCsrfToken(cookie.value),
                set_cookie=False,
            )
        token = OAuthCsrfToken(self._generator())
        return OAuthCsrfIssued(token=token, set_cookie=True)

    def validate(
        self,
        cookie: OAuthCsrfCookieState,
        form: OAuthCsrfFormState,
    ) -> OAuthCsrfValidation:
        if not isinstance(cookie, OAuthCsrfCookieProvided):
            return OAuthCsrfRejected()
        if not isinstance(form, OAuthCsrfFormProvided):
            return OAuthCsrfRejected()
        if not _usable(cookie.value) or not _usable(form.value):
            return OAuthCsrfRejected()
        if cookie.value != form.value:
            return OAuthCsrfRejected()
        return OAuthCsrfAccepted()
