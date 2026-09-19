from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class OAuthClientName:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("oauth client name must not be empty")


@dataclass(slots=True, frozen=True)
class OAuthAppDisplayName:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("oauth app display name must not be empty")


@dataclass(slots=True, frozen=True)
class OAuthAppIconReference:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("oauth app icon reference must not be empty")
