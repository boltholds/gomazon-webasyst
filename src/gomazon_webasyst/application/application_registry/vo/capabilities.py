from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ApplicationCapabilityName:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("application capability name must not be empty")


@dataclass(slots=True, frozen=True)
class ApplicationCapabilities:
    values: frozenset[ApplicationCapabilityName]
