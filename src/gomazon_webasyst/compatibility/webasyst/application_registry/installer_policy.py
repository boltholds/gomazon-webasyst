from dataclasses import dataclass
from typing import Protocol


class LegacyInstallerActivationPolicy(Protocol):
    def should_force_enable(self) -> bool: ...


@dataclass(slots=True, frozen=True)
class NeverForceInstaller:
    def should_force_enable(self) -> bool:
        return False


@dataclass(slots=True, frozen=True)
class StaticInstallerActivationPolicy:
    enabled: bool

    def should_force_enable(self) -> bool:
        return self.enabled
