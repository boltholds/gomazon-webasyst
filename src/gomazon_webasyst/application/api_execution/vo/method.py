from dataclasses import dataclass
import re

from gomazon_webasyst.application.access_values import AppId


_HTTP_TOKEN = re.compile(r"^[!#$%&'*+.^_\x60|~0-9A-Za-z-]+$")


@dataclass(slots=True, frozen=True)
class ApiMethodName:
    value: str

    def __post_init__(self) -> None:
        if not self.value or self.value != self.value.strip():
            raise ValueError("api method name must be non-empty and trimmed")


@dataclass(slots=True, frozen=True)
class ApiMethodTarget:
    app_id: AppId
    method: ApiMethodName


@dataclass(slots=True, frozen=True)
class ApiHttpMethod:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.upper()
        if not normalized or _HTTP_TOKEN.fullmatch(normalized) is None:
            raise ValueError("invalid HTTP method token")
        object.__setattr__(self, "value", normalized)
