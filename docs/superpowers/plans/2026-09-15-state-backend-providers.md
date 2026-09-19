# State Backend Providers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Remove the hard-coded in-process auth session store from composition and make `SessionStateStore` selectable through an extensible provider/factory/registry seam, with `memory` remaining the default.

**Architecture:** `SessionStateStore` remains the application-owned port. Provider names, factories, registration, and selection live in composition; concrete stores remain infrastructure adapters. One application container resolves one store instance and shares it across all auth/session use cases. New providers register factories rather than adding a centralized backend switch.

**Tech Stack:** Python 3.12+, Pydantic Settings v2, dataclasses/Protocols, pytest.

**Spec:** `docs/superpowers/specs/2026-09-15-state-backends-api-oauth2-design.md`

## Global Constraints

- Application code must not import concrete memory/Redis/Supabase implementations.
- Expected negative outcomes use explicit typed variants, never `None`, `Optional`, empty strings, or bool sentinels.
- `StateProviderName` is open/extensible and therefore is not an enum.
- `composition/auth.py` must no longer construct `InMemorySessionStateStore` directly.
- Exactly one resolved `SessionStateStore` instance is shared by all auth/session use cases in one container.
- No Redis or Supabase dependency is added in this slice.
- Existing in-memory behavior stays unchanged: generated opaque id, 30-minute inactivity TTL, touch on resolve, expiry deletion, idempotent revoke, explicit collision.
- No centralized `if provider == ...` selector is allowed.

---

### Task 1: Provider value, result variants, factory protocol, and registry

**Files:**
- Create: `src/gomazon_webasyst/composition/session_state_providers.py`
- Create: `tests/unit/test_session_state_provider_registry.py`

**Interfaces:**
- Produces `StateProviderName(value: str)`.
- Produces `SessionStateStoreFactory.create() -> SessionStateStore`.
- Produces explicit `ProviderRegistered`, `ProviderRegistrationRejected`, `ProviderResolved`, `ProviderUnknown` results.
- Produces `SessionStateProviderRegistry.register(...)` and `.resolve(...)`.

- [x] **Step 1: Write failing value/registry tests**

```python
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


def test_state_provider_name_rejects_empty_value():
    with pytest.raises(ValueError):
        StateProviderName("")


def test_registry_registers_resolves_and_rejects_duplicate_without_none():
    factory = object()
    registry = SessionStateProviderRegistry()
    name = StateProviderName("memory")

    first = registry.register(name, factory)
    duplicate = registry.register(name, object())
    resolved = registry.resolve(name)
    missing = registry.resolve(StateProviderName("redis"))

    assert isinstance(first, ProviderRegistered)
    assert isinstance(duplicate, ProviderRegistrationRejected)
    assert isinstance(resolved, ProviderResolved)
    assert resolved.factory is factory
    assert isinstance(missing, ProviderUnknown)
```

- [x] **Step 2: Run RED**

Run: `python -m pytest tests/unit/test_session_state_provider_registry.py -v`
Expected: FAIL because `composition.session_state_providers` does not exist.

- [x] **Step 3: Implement minimal immutable provider types and registry**

```python
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
```

`SessionStateProviderRegistry` owns a private dictionary, but its public API returns only the explicit variants above. Duplicate registration must preserve the original factory.

- [x] **Step 4: Run GREEN**

Run: `python -m pytest tests/unit/test_session_state_provider_registry.py -v`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add src/gomazon_webasyst/composition/session_state_providers.py tests/unit/test_session_state_provider_registry.py
git commit -m "feat: add session state provider registry"
```

### Task 2: Memory factory and default provider registry

**Files:**
- Modify: `src/gomazon_webasyst/composition/session_state_providers.py`
- Test: `tests/unit/test_session_state_provider_registry.py`
- Existing adapter under test: `src/gomazon_webasyst/infrastructure/sessions/memory.py`

**Interfaces:**
- Consumes existing `InMemorySessionStateStore`.
- Produces `InMemorySessionStateStoreFactory`.
- Produces `create_default_session_state_provider_registry()` with exactly the `memory` provider registered.
- Produces `resolve_session_state_store(registry, name) -> SessionStateStore | raises UnknownSessionStateProviderError` only at the composition bootstrap boundary; unknown provider is not represented as `None`.

- [x] **Step 1: Write failing factory/default-registry tests**

```python
from gomazon_webasyst.infrastructure.sessions.memory import InMemorySessionStateStore


def test_default_registry_resolves_memory_factory():
    registry = create_default_session_state_provider_registry()
    result = registry.resolve(StateProviderName("memory"))

    assert isinstance(result, ProviderResolved)
    assert isinstance(result.factory.create(), InMemorySessionStateStore)


def test_resolving_unknown_provider_fails_at_composition_boundary():
    registry = create_default_session_state_provider_registry()

    with pytest.raises(UnknownSessionStateProviderError):
        resolve_session_state_store(registry, StateProviderName("redis"))
```

- [x] **Step 2: Run RED**

Run: `python -m pytest tests/unit/test_session_state_provider_registry.py -v`
Expected: FAIL for missing memory factory/default registry.

- [x] **Step 3: Implement factory and bootstrap resolver**

`InMemorySessionStateStoreFactory` accepts optional constructor configuration as real concrete values (`ttl`, `clock`, `session_id_factory`) and returns a new `InMemorySessionStateStore`. The default registry registers only `StateProviderName("memory")`.

The bootstrap resolver pattern is:

```python
def resolve_session_state_store(
    registry: SessionStateProviderRegistry,
    name: StateProviderName,
) -> SessionStateStore:
    result = registry.resolve(name)
    if isinstance(result, ProviderResolved):
        return result.factory.create()
    raise UnknownSessionStateProviderError(name.value)
```

- [x] **Step 4: Run GREEN plus existing memory-store tests**

Run: `python -m pytest tests/unit/test_session_state_provider_registry.py tests/unit/test_session_state_store.py -v`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add src/gomazon_webasyst/composition/session_state_providers.py tests/unit/test_session_state_provider_registry.py
git commit -m "feat: add default memory session provider"
```

### Task 3: Inject `SessionStateStore` into auth composition

**Files:**
- Modify: `src/gomazon_webasyst/composition/auth.py`
- Modify: `tests/unit/test_auth_container.py`
- Modify: `tests/unit/test_persistent_login_container.py`

**Interfaces:**
- `create_auth_use_cases(session_factory, *, session_state: SessionStateStore, ...) -> AuthUseCases`.
- `create_auth_use_cases_with_persistent_credentials(session_factory, *, session_state: SessionStateStore, persistent_resolver, persistent_issuer, ...) -> AuthUseCases`.
- `_create_auth_foundation(..., session_state: SessionStateStore, ...)` reuses exactly the supplied object.

- [x] **Step 1: Change tests first to require explicit store injection and identity preservation**

```python
class StubSessionStateStore:
    async def create(self, request):
        raise AssertionError("not called")
    async def resolve(self, session_id):
        raise AssertionError("not called")
    async def revoke(self, key):
        raise AssertionError("not called")


def test_auth_composition_reuses_supplied_session_state_store():
    state = StubSessionStateStore()
    auth = create_auth_use_cases(object(), session_state=state)

    assert auth.resolve_backend_session._session_state is state
    assert auth.logout_backend_session._session_state is state
    assert auth.authenticate_backend_password._session_establisher._session_state is state
```

Update every existing composition test call so no implicit memory backend remains.

- [x] **Step 2: Run RED**

Run: `python -m pytest tests/unit/test_auth_container.py tests/unit/test_persistent_login_container.py -v`
Expected: FAIL because current signatures do not accept/require `session_state`.

- [x] **Step 3: Refactor auth composition**

Remove:

```python
from gomazon_webasyst.infrastructure.sessions.memory import InMemorySessionStateStore
...
session_state = InMemorySessionStateStore()
```

Pass the injected store into `_AuthFoundation`, `BackendSessionEstablisher`, resolve, logout, and persistent restore through the existing shared establisher.

- [x] **Step 4: Run GREEN**

Run: `python -m pytest tests/unit/test_auth_container.py tests/unit/test_persistent_login_container.py tests/unit/test_auth_use_cases.py tests/unit/test_persistent_login_use_cases.py -v`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add src/gomazon_webasyst/composition/auth.py tests/unit/test_auth_container.py tests/unit/test_persistent_login_container.py
git commit -m "refactor: inject auth session state store"
```

### Task 4: Settings and container-level provider selection

**Files:**
- Modify: `src/gomazon_webasyst/composition/settings.py`
- Modify: `src/gomazon_webasyst/composition/container.py`
- Modify: `tests/unit/test_settings.py`
- Modify: `tests/unit/test_container.py`
- Modify: `tests/unit/test_auth_container.py`

**Interfaces:**
- `Settings.session_state_provider: str = "memory"` normalized through `StateProviderName` at composition.
- `create_container(settings)` uses the default registry.
- `create_container_with_session_state_registry(settings, *, session_state_registry)` allows custom deployments.
- Both entry points resolve one store exactly once before auth use-case construction.

- [x] **Step 1: Write failing settings tests**

```python
def test_default_session_state_provider_is_memory():
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    assert settings.session_state_provider == "memory"


def test_custom_session_state_provider_name_is_accepted():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        session_state_provider="redis",
    )
    assert settings.session_state_provider == "redis"
```

- [x] **Step 2: Write failing container custom-provider test**

Use a `RecordingFactory` whose `create()` increments a counter and returns one sentinel store. Assert `create_container_with_session_state_registry(...)` calls it once and all auth use cases reference that same sentinel store.

- [x] **Step 3: Run RED**

Run: `python -m pytest tests/unit/test_settings.py tests/unit/test_container.py tests/unit/test_auth_container.py -v`
Expected: FAIL for missing setting/entry point.

- [x] **Step 4: Implement settings and container selection**

Default `create_container(settings)` creates the default registry then delegates to `create_container_with_session_state_registry(...)`. The custom entry point converts the string to `StateProviderName`, resolves the factory, creates one store, and passes it to `create_auth_use_cases(session_factory, session_state=store)`.

There must be no provider-name branch in `container.py`.

- [x] **Step 5: Run GREEN**

Run: `python -m pytest tests/unit/test_settings.py tests/unit/test_container.py tests/unit/test_auth_container.py -v`
Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add src/gomazon_webasyst/composition/settings.py src/gomazon_webasyst/composition/container.py tests/unit/test_settings.py tests/unit/test_container.py tests/unit/test_auth_container.py
git commit -m "feat: select session state provider in composition"
```

### Task 5: Contract guard and full verification

**Files:**
- Create: `tests/architecture/test_session_state_provider_boundaries.py`
- Modify only if needed: `tests/architecture/test_no_optional_result_contracts.py`
- Modify: `AGENTS.md`

**Interfaces:**
- Architecture test pins that application modules do not import `composition.session_state_providers` or `infrastructure.sessions.memory`.
- Architecture test pins that `composition/auth.py` does not import `InMemorySessionStateStore`.
- `AGENTS.md` records the provider-selection decision and future Redis/Supabase adapter rule.

- [x] **Step 1: Write architecture guard**

```python
def test_auth_composition_does_not_select_concrete_session_backend():
    source = Path("src/gomazon_webasyst/composition/auth.py").read_text()
    assert "InMemorySessionStateStore" not in source
    assert "infrastructure.sessions.memory" not in source


def test_application_does_not_import_session_provider_registry():
    for path in Path("src/gomazon_webasyst/application").rglob("*.py"):
        source = path.read_text()
        assert "composition.session_state_providers" not in source
```

- [x] **Step 2: Run focused architecture suite**

Run: `python -m pytest tests/architecture/test_session_state_provider_boundaries.py tests/architecture/test_no_optional_result_contracts.py -v`
Expected: PASS.

- [x] **Step 3: Record ADR in `AGENTS.md`**

Add the next ADR stating:

- runtime session state is selected at composition through an extensible provider registry;
- application ports remain domain-specific;
- providers create stores, not per-request repositories;
- one store instance is shared per container;
- Redis/Supabase adapters must pass the same `SessionStateStore` contract;
- Supabase Realtime may propagate invalidation but durable Postgres state remains authoritative.

- [x] **Step 4: Run complete verification**

Run:

```bash
python -m compileall -q src tests
python -m pytest -v
```

Expected: compile success and entire test suite green.

- [x] **Step 5: Commit completion**

```bash
git add tests/architecture/test_session_state_provider_boundaries.py tests/architecture/test_no_optional_result_contracts.py AGENTS.md
git commit -m "test: guard session state provider boundaries"
```


## Implementation Status

Implemented on `feature/state-backends-api-oauth2`.

Verification on branch head lineage:

- GitHub Actions Python 3.12: **316 passed, 0 failed, 0 skipped**.
- CI **Compile source tree** step: success.
- Session-state backend selection is registry/factory based; auth composition no longer constructs the concrete memory store.
- Default provider remains `memory`; custom providers can be registered without application-layer changes.
- `InMemorySessionStateStoreFactory` forwards configurable session-id generation, clock and TTL into the concrete memory adapter.
- A reusable `SessionStateStore` contract suite now pins collision, TTL refresh/expiry, wrong-key revoke and idempotent revoke semantics for future Redis/Supabase adapters.
- API OAuth2 credential core maps the existing `wa_api_auth_codes` and `wa_api_tokens` tables and exposes issue/exchange/implicit/resolve/revoke use cases without mounting HTTP OAuth routes.
- Architecture and Optional/nullability guards pass.
