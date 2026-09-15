from dataclasses import dataclass
from typing import Protocol

from gomazon_webasyst.application.ports.session_state import SessionStateStore


@dataclass(slots=True, frozen=True)
class StateProviderName:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("state provider name must not be empty")


class SessionStateStoreFactory(Protocol):
    def create(self) -> SessionStateStore: ...


@dataclass(slots=True, frozen=True)
class ProviderRegistered:
    name: StateProviderName


@dataclass(slots=True, frozen=True)
class ProviderRegistrationRejected:
    name: StateProviderName


@dataclass(slots=True, frozen=True)
class ProviderResolved:
    name: StateProviderName
    factory: SessionStateStoreFactory


@dataclass(slots=True, frozen=True)
class ProviderUnknown:
    name: StateProviderName


ProviderRegistrationResult = ProviderRegistered | ProviderRegistrationRejected
ProviderResolution = ProviderResolved | ProviderUnknown


class SessionStateProviderRegistry:
    def __init__(self) -> None:
        self._factories: dict[StateProviderName, SessionStateStoreFactory] = {}

    def register(
        self,
        name: StateProviderName,
        factory: SessionStateStoreFactory,
    ) -> ProviderRegistrationResult:
        if name in self._factories:
            return ProviderRegistrationRejected(name=name)
        self._factories[name] = factory
        return ProviderRegistered(name=name)

    def resolve(self, name: StateProviderName) -> ProviderResolution:
        if name not in self._factories:
            return ProviderUnknown(name=name)
        return ProviderResolved(name=name, factory=self._factories[name])
