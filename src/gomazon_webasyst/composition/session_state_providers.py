from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import uuid4

from gomazon_webasyst.application.auth_values import SessionId
from gomazon_webasyst.application.ports.session_state import SessionStateStore
from gomazon_webasyst.infrastructure.sessions.memory import InMemorySessionStateStore


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


def _default_session_id() -> SessionId:
    return SessionId(uuid4().hex)


@dataclass(slots=True, frozen=True)
class InMemorySessionStateStoreFactory:
    session_id_factory: Callable[[], SessionId] = _default_session_id
    clock: Callable[[], datetime] = datetime.now
    ttl: timedelta = timedelta(minutes=30)

    def create(self) -> SessionStateStore:
        return InMemorySessionStateStore(
            session_id_factory=self.session_id_factory,
            clock=self.clock,
            ttl=self.ttl,
        )


class UnknownSessionStateProviderError(RuntimeError):
    def __init__(self, provider: StateProviderName) -> None:
        self.provider = provider
        super().__init__(f"unknown session state provider: {provider.value}")


def create_default_session_state_provider_registry() -> SessionStateProviderRegistry:
    registry = SessionStateProviderRegistry()
    registration = registry.register(
        StateProviderName("memory"),
        InMemorySessionStateStoreFactory(),
    )
    if isinstance(registration, ProviderRegistrationRejected):
        raise RuntimeError("default memory session state provider was registered twice")
    return registry


def resolve_session_state_store(
    registry: SessionStateProviderRegistry,
    name: StateProviderName,
) -> SessionStateStore:
    result = registry.resolve(name)
    if isinstance(result, ProviderResolved):
        return result.factory.create()
    raise UnknownSessionStateProviderError(result.name)
