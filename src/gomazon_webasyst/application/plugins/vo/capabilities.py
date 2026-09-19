from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PluginCapabilityName:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("plugin capability name must not be empty")


@dataclass(slots=True, frozen=True)
class PluginCapabilities:
    values: frozenset[PluginCapabilityName]
