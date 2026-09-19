from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ApiApplicationErrorCode:
    value: str

    def __post_init__(self) -> None:
        if not self.value or self.value != self.value.strip():
            raise ValueError("api application error code must be non-empty and trimmed")
