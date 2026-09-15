from dataclasses import dataclass

from gomazon_webasyst.application.access_values import AppId


@dataclass(slots=True, frozen=True)
class AuthorizationCode:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("authorization code must not be empty")


@dataclass(slots=True, frozen=True)
class ApiAccessToken:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("api access token must not be empty")


@dataclass(slots=True, frozen=True)
class ApiClientId:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("api client id must not be empty")


@dataclass(slots=True, frozen=True)
class ApiScope:
    apps: tuple[AppId, ...]

    def __post_init__(self) -> None:
        unique = tuple(dict.fromkeys(self.apps))
        if not unique:
            raise ValueError("api scope must not be empty")
        object.__setattr__(self, "apps", unique)

    @classmethod
    def of(cls, *app_ids: str) -> "ApiScope":
        return cls(tuple(AppId(app_id) for app_id in app_ids))
