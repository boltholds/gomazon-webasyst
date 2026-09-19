from dataclasses import dataclass


def _require_non_empty(value: str, label: str) -> None:
    if not value:
        raise ValueError(f"{label} must not be empty")


@dataclass(slots=True, frozen=True)
class ApplicationDisplayName:
    value: str

    def __post_init__(self) -> None:
        _require_non_empty(self.value, "application display name")


@dataclass(slots=True, frozen=True)
class ApplicationVendor:
    value: str

    def __post_init__(self) -> None:
        _require_non_empty(self.value, "application vendor")


@dataclass(slots=True, frozen=True)
class ApplicationVersion:
    value: str

    def __post_init__(self) -> None:
        _require_non_empty(self.value, "application version")
