from dataclasses import FrozenInstanceError

import pytest

from gomazon_webasyst.composition.session_state_providers import (
    ProviderRegistered,
    ProviderRegistrationRejected,
    ProviderResolved,
    ProviderUnknown,
    SessionStateProviderRegistry,
    StateProviderName,
)


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
