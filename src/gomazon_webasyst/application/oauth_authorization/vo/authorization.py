from dataclasses import dataclass
from typing import TypeAlias

from gomazon_webasyst.application.access_values import AppId


@dataclass(slots=True, frozen=True)
class OAuthRedirectUri:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("oauth redirect uri must not be empty")


@dataclass(slots=True, frozen=True)
class OAuthCsrfToken:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("oauth csrf token must not be empty")


@dataclass(slots=True, frozen=True)
class OAuthRequestedScope:
    apps: tuple[AppId, ...]

    def __post_init__(self) -> None:
        unique = tuple(dict.fromkeys(self.apps))
        if not unique:
            raise ValueError("oauth requested scope must not be empty")
        object.__setattr__(self, "apps", unique)


@dataclass(slots=True, frozen=True)
class OAuthRedirectProvided:
    uri: OAuthRedirectUri


@dataclass(slots=True, frozen=True)
class OAuthRedirectMissing:
    pass


OAuthRedirectTarget: TypeAlias = OAuthRedirectProvided | OAuthRedirectMissing
