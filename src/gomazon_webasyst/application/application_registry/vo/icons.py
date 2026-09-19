from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ApplicationIconReference:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("application icon reference must not be empty")


@dataclass(slots=True, frozen=True)
class ApplicationIcon:
    size: int
    reference: ApplicationIconReference

    def __post_init__(self) -> None:
        if self.size <= 0:
            raise ValueError("application icon size must be positive")


@dataclass(slots=True, frozen=True)
class ApplicationIconSet:
    items: tuple[ApplicationIcon, ...]

    def __post_init__(self) -> None:
        sizes = [item.size for item in self.items]
        if len(sizes) != len(set(sizes)):
            raise ValueError("duplicate application icon size")
