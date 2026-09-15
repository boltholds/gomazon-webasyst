from dataclasses import FrozenInstanceError

import pytest

from gomazon_webasyst.composition.session_state_providers import (
    ProviderRegistered,
    ProviderRegistrationRejected,
    ProviderResolved,
    ProviderUnknown,
    SessionStateProviderRegistry,
    StateProviderName,
    UnknownSessionStateProviderError,
    create_default_session_state_provider_registry,
    resolve_session_state_store,
)
from gomazon_webasyst.infrastructure.sessions.memory import InMemorySessionStateStore


def test_state_provider_name_rejects_empty_value() -> None:
    with pytest.raises(ValueError):
        StateProviderName("")


def test_state_provider_name_rejects_whitespace_only_value() -> None:
    with pytest.raises(ValueError):
        StateProviderName("   ")


def test_state_provider_name_is_frozen_and_hashable() -> None:
    name = StateProviderName("memory")

    assert {name}
    with pytest.raises(FrozenInstanceError):
        name.value = "redis"  # type: ignore[misc]


def test_registry_registers_resolves_and_rejects_duplicate_without_none() -> None:
    first_factory = object()
    replacement_factory = object()
    registry = SessionStateProviderRegistry()
    name = StateProviderName("memory")

    first = registry.register(name, first_factory)
    duplicate = registry.register(name, replacement_factory)
    resolved = registry.resolve(name)
    missing = registry.resolve(StateProviderName("redis"))

    assert isinstance(first, ProviderRegistered)
    assert first.name == name
    assert isinstance(duplicate, ProviderRegistrationRejected)
    assert duplicate.name == name
    assert isinstance(resolved, ProviderResolved)
    assert resolved.name == name
    assert resolved.factory is first_factory
    assert isinstance(missing, ProviderUnknown)
    assert missing.name == StateProviderName("redis")


def test_default_registry_resolves_memory_factory() -> None:
    registry = create_default_session_state_provider_registry()
    result = registry.resolve(StateProviderName("memory"))

    assert isinstance(result, ProviderResolved)
    assert isinstance(result.factory.create(), InMemorySessionStateStore)


def test_resolve_session_state_store_uses_registered_factory_once() -> None:
    class RecordingFactory:
        def __init__(self) -> None:
            self.calls = 0
            self.store = InMemorySessionStateStore()

        def create(self):
            self.calls += 1
            return self.store

    factory = RecordingFactory()
    registry = SessionStateProviderRegistry()
    registry.register(StateProviderName("custom"), factory)

    store = resolve_session_state_store(registry, StateProviderName("custom"))

    assert store is factory.store
    assert factory.calls == 1


def test_resolving_unknown_provider_fails_at_composition_boundary() -> None:
    registry = create_default_session_state_provider_registry()

    with pytest.raises(UnknownSessionStateProviderError) as exc_info:
        resolve_session_state_store(registry, StateProviderName("redis"))

    assert exc_info.value.provider == StateProviderName("redis")
