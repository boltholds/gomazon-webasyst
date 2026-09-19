from dataclasses import dataclass
import re

from gomazon_webasyst.contracts.enums import CookieSameSite


_COOKIE_TOKEN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")


@dataclass(slots=True, frozen=True)
class CookieName:
    value: str

    def __post_init__(self) -> None:
        if not self.value or self.value.strip() != self.value:
            raise ValueError("cookie name must be a non-empty token")
        if _COOKIE_TOKEN.fullmatch(self.value) is None:
            raise ValueError("cookie name contains invalid characters")


@dataclass(slots=True, frozen=True)
class BackendAuthCookiePolicy:
    session_name: CookieName
    persistent_name: CookieName
    secure: bool
    path: str
    same_site: CookieSameSite

    def __post_init__(self) -> None:
        if not self.path or not self.path.startswith("/"):
            raise ValueError("cookie path must start with '/'")
