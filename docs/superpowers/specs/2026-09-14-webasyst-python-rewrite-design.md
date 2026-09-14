# Webasyst 4.2.0 Python Rewrite — Design Specification

Status: accepted baseline
Date: 2026-09-14
Repository: `boltholds/gomazon-webasyst`

## 1. Goal

Rewrite the supplied Webasyst Framework 4.2.0 service in Python while preserving externally relevant behavior and legacy data compatibility where required.

The rewrite must not mechanically translate PHP classes. It must preserve contracts and behavior while replacing the framework internals with explicit typed boundaries, dependency injection, testable use cases, and replaceable infrastructure adapters.

Two requirements are architectural invariants:

1. Persistence must be replaceable through dependency injection. Application code must not depend on a concrete database, SQLAlchemy session, SQL dialect, or ORM model.
2. Architectural contracts must be represented by Pydantic v2 models.

`AGENTS.md` is the canonical architecture record. This design expands the accepted decisions there and must not contradict it.

## 2. Legacy source inventory

The supplied archive contains 7,569 files, including 2,468 PHP files.

Top-level legacy areas:

- `wa-system/` — 1,574 files; framework runtime and shared infrastructure.
- `wa-apps/` — 4,232 files; bundled applications.
- `wa-content/` — 1,028 files; assets/content.
- `wa-plugins/` — 584 files.
- `wa-widgets/` — 114 files.
- `wa-installer/` — installer bootstrap.
- `wa-config/` — framework configuration.
- entry points: `index.php`, `api.php`, `cli.php`, `wa.php`, `install.php`.

Largest bundled applications:

- `site` — 1,345 files.
- `developer` — 975 files.
- `blog` — 584 files.
- `photos` — 567 files.
- `team` — 413 files.
- `installer` — 157 files.
- `ui` — 113 files.
- `apiexplorer` — 60 files.
- `dummy` — 17 files.

Important framework surfaces observed in the source:

- `waSystem` — runtime/service locator, configuration, dispatch, app/plugin/event access.
- `waRouting` — domain/path routing, route matching and URL generation.
- `waModel` and `waDb*` — query execution, metadata, CRUD, transactions, database adapters.
- `waFrontController`, `waController`, `waAction` — request dispatch/controller execution.
- `waAPIController`, `waAPIMethod` — API dispatch, access checks and token handling.
- `waAuth`, `waOAuth2Adapter` — authentication, login lookup, cookies/tokens and OAuth providers.
- `waEvent` — app/plugin event discovery and dispatch.
- `waPlugin` / `waPlugins` — plugin lifecycle, settings, routing, cron, templates/assets.

The legacy entry point `index.php` constructs `waSystem` and dispatches the request. `api.php` enters the API subsystem, while CLI entry points route through the same framework runtime.

## 3. Target architecture

Target stack:

- Python 3.12+
- FastAPI / Starlette
- Pydantic v2
- `pydantic-settings`
- SQLAlchemy 2.x as the first relational persistence adapter
- Alembic for Python-owned schema migrations
- pytest

The target dependency direction is:

```text
presentation / compatibility adapters
                |
                v
          application use cases
                |
                v
       contracts + application ports
                ^
                |
       infrastructure implementations
```

No lower-level adapter may become the API of an upper-level layer.

## 4. Package boundaries

Initial target layout:

```text
src/
  gomazon_webasyst/
    main.py

    composition/
      container.py
      settings.py

    contracts/
      common.py
      contacts.py
      auth.py
      routing.py
      permissions.py
      api.py
      plugins.py

    application/
      commands/
      queries/
      services/
      ports/
        repositories.py
        unit_of_work.py
        auth.py
        cache.py
        filesystem.py
        events.py
        plugins.py

    infrastructure/
      persistence/
        sqlalchemy/
          models/
          repositories/
          mappings.py
          unit_of_work.py
          factory.py
      auth/
      cache/
      filesystem/
      events/
      plugins/

    compatibility/
      webasyst/
        routing/
        auth/
        api/
        config/
        plugins/

    presentation/
      http/
        api/
        web/
        dependencies.py
      cli/

tests/
  unit/
  integration/
  compatibility/
  migration/
```

Feature-local packaging may replace broad horizontal folders as the codebase grows, but dependency direction must remain unchanged.

## 5. Dependency injection and composition root

The old `waSystem` combines dispatch, service location, factories, configuration, user state, plugin access, routing and many infrastructure concerns. The Python rewrite must not reproduce this as a global singleton.

A composition root will construct concrete dependencies at process startup.

It owns:

- settings,
- persistence backend selection,
- engine/connection resources,
- Unit of Work factory,
- repository implementations,
- cache implementation,
- filesystem/storage implementation,
- auth provider implementations,
- event bus/plugin registry implementations,
- application services,
- FastAPI dependency adapters.

Application services use constructor injection and remain directly constructible in tests.

FastAPI `Depends` is allowed only in the presentation/composition boundary. `Depends` must not appear in application services or contracts.

No module-level mutable service locator or global database session is allowed.

## 6. Persistence architecture

### 6.1 Port owned by the application

The application owns repository and Unit of Work protocols.

Example shape:

```python
from typing import Protocol

class ContactRepository(Protocol):
    async def get(self, contact_id: int) -> "ContactRead | None": ...
    async def create(self, data: "ContactCreate") -> "ContactRead": ...
    async def update(self, contact_id: int, data: "ContactUpdate") -> "ContactRead": ...

class UnitOfWork(Protocol):
    contacts: ContactRepository

    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...

class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...
```

Exact repository methods are defined by use-case needs. Repositories must expose intent-oriented operations, not generic SQL/query-builder objects.

### 6.2 First adapter

The first adapter uses SQLAlchemy 2.x and the existing Webasyst relational schema where feasible.

SQLAlchemy types must remain inside `infrastructure.persistence.sqlalchemy`:

- `Engine` / `AsyncEngine`
- `Session` / `AsyncSession`
- ORM declarative classes
- SQLAlchemy statements/results
- dialect-specific SQL

These types must never be returned from repositories or accepted by application services.

### 6.3 Database replacement

Database choice is assembled through DI.

A change from MySQL/MariaDB to PostgreSQL must require changes only to configuration and, where dialect differences demand it, infrastructure adapter code.

It must not require changes to:

- application services,
- Pydantic contracts,
- route handlers except wiring,
- authorization policy,
- business rules.

SQLAlchemy's multi-dialect support is useful but does not itself satisfy the requirement. The architectural seam is the application-owned repository/UoW port.

### 6.4 Transactions

Transaction scope is explicit at the use-case level through Unit of Work.

Use cases may request commit/rollback behavior but must never manipulate a SQLAlchemy session directly.

Nested transaction/savepoint support, if needed later for legacy behavior, will be added as a capability of the UoW port rather than leaking SQLAlchemy APIs upward.

## 7. Pydantic contract policy

Pydantic v2 models define architectural contracts and external/input-output DTOs.

Separate models by semantics. Example:

```python
class ContactCreate(BaseModel):
    name: str
    email: EmailStr | None = None

class ContactUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None

class ContactRead(BaseModel):
    id: int
    name: str
    email: EmailStr | None = None
```

Rules:

- no SQLAlchemy inheritance or persistence methods,
- no hidden I/O in validators,
- explicit aliases for legacy field names,
- strict types where legacy coercion would hide errors,
- API contracts must be versionable,
- public compatibility contracts require characterization tests,
- ORM-to-contract conversion occurs at a controlled infrastructure boundary.

Pydantic models are not a replacement for business policy. Complex domain behavior may later live in dedicated domain services/entities, but their external boundaries remain Pydantic contracts.

## 8. Legacy-to-Python subsystem mapping

### `waSystem`

Replace with:

- composition root,
- typed settings,
- explicit service construction,
- request-scoped dependencies.

Do not recreate a universal `System.get_instance()` object.

### `waRouting`

Replace with two cooperating layers:

1. native FastAPI/Starlette routes for new Python endpoints,
2. Webasyst compatibility route resolver for legacy domain/path rules and URL generation.

Compatibility routing should produce/consume Pydantic contracts such as `RouteRequest`, `RouteMatch`, and `RouteBuildRequest` rather than legacy associative arrays.

### `waModel` / `waDb*`

Replace with:

- application repository protocols,
- Unit of Work protocol,
- SQLAlchemy repository/UoW adapter,
- migration/compatibility mappings for legacy tables.

Generic calls such as `query($sql)` must not become a generic SQL escape hatch exposed to application code.

### `waFrontController` / `waController` / `waAction`

Replace with:

- FastAPI/Starlette presentation handlers,
- compatibility dispatch adapter,
- application commands/queries/services.

Controller classes should be thin transport adapters; use cases hold application behavior.

### `waAPIController` / `waAPIMethod`

Replace with:

- typed FastAPI routers,
- API authentication dependency,
- application authorization policy,
- compatibility serializer for legacy response/error envelopes where required.

### `waAuth` / OAuth adapters

Split into:

- authentication service/use cases,
- identity/session/token contracts,
- password verification port,
- session/token persistence ports,
- OAuth provider adapter interface,
- concrete provider adapters.

Cookie parsing and OAuth HTTP mechanics remain infrastructure/presentation concerns.

### `waEvent`

Replace with a typed event bus port and explicit event contracts.

Legacy event names/payloads are translated by the Webasyst compatibility bridge.

Event discovery from arbitrary PHP files is not reproduced in the core architecture.

### `waPlugin`

Replace dynamic PHP plugin semantics with:

- plugin manifest contract,
- plugin registry,
- typed hook/event interfaces,
- adapter for legacy naming and configuration where compatibility is required.

Plugin loading must be explicit and observable; arbitrary runtime imports must not become a hidden dependency system.

## 9. Compatibility strategy

Compatibility is measured per boundary, not assumed globally.

For every migrated endpoint or behavior, record:

- method,
- path/domain matching,
- input parsing,
- auth requirements,
- permission checks,
- status code,
- JSON/body shape,
- redirects,
- cookies/session mutation,
- error semantics.

Where practical, capture representative legacy behavior as golden/characterization fixtures before replacement.

The compatibility layer owns Webasyst-specific conventions. New application code must not depend on `wa*` naming or PHP array semantics.

## 10. Existing database and schema migration

The initial rewrite must prefer using the existing Webasyst schema rather than redesigning it immediately.

Reasons:

- reduces migration risk,
- permits behavioral comparison,
- allows staged cutover,
- preserves existing customer/application data.

Schema redesign is deferred until a migrated subsystem has stable contracts and characterization tests.

Alembic migrations are used only for schema changes owned by the Python rewrite. Existing legacy schema must first be reflected/mapped explicitly rather than re-created blindly.

## 11. First vertical slice

The first implementation milestone will prove the architectural seams with the contact subsystem, because contacts/users are foundational to authentication and permissions.

Scope:

1. project packaging and test harness,
2. settings and composition root,
3. `ContactRead`, `ContactCreate`, `ContactUpdate` Pydantic contracts,
4. `ContactRepository` protocol,
5. `UnitOfWork` and `UnitOfWorkFactory` protocols,
6. SQLAlchemy adapter mapped to the relevant legacy contact table(s),
7. one read use case,
8. one write/update use case,
9. thin FastAPI endpoints for the new Python interface,
10. unit tests using fake repositories/UoW,
11. persistence contract tests,
12. integration tests against the concrete SQLAlchemy adapter.

This milestone is architectural proof, not a claim of Webasyst API parity.

Before claiming legacy compatibility for contacts, the existing `waContact`/related model behavior must be characterized and a separate compatibility adapter added.

## 12. Migration sequence

After the first vertical slice:

### Phase A — runtime foundations

- configuration,
- composition root,
- logging/error model,
- request context,
- persistence infrastructure,
- cache/filesystem ports as needed.

### Phase B — routing and dispatch compatibility

- domain/path route parsing,
- route match contract,
- URL building,
- legacy front-controller compatibility.

### Phase C — identity and security

- contacts/users,
- sessions,
- password auth,
- OAuth provider ports/adapters,
- permissions/groups,
- API tokens/auth codes.

### Phase D — API framework

- API dispatch conventions,
- error envelopes,
- access checks,
- versioning/serialization compatibility.

### Phase E — extensibility

- event bus,
- hook bridge,
- plugin manifests/registry,
- plugin settings,
- cron/CLI extension points.

### Phase F — bundled applications

Port applications vertically, prioritizing dependencies and actual product needs rather than file count. Likely order:

1. `team`/identity-adjacent behavior required by the product,
2. `site`,
3. product-required portions of `blog`/`photos`,
4. developer/admin tooling,
5. installer/updater compatibility only if still needed in the Python deployment model.

The order may change after route/data dependency analysis.

## 13. Error model

Application errors must be framework-agnostic typed exceptions/results.

Presentation adapters translate them to HTTP responses. Compatibility adapters may translate the same errors to legacy Webasyst error envelopes.

Infrastructure exceptions such as SQLAlchemy/driver exceptions must be translated before crossing the persistence boundary when they are meaningful to application behavior.

Unexpected infrastructure failures are logged with causal context and surfaced as generic application/infrastructure failures rather than leaking driver internals.

## 14. Testing design

### Unit

Application use cases use fake repositories/UoW and require no database or ASGI server.

### Persistence contract

Reusable tests define expected repository behavior. Every relational adapter must pass the same contract suite.

### Integration

Test SQLAlchemy mappings, transaction behavior, constraints and concrete wiring.

### HTTP

Use ASGI-level tests for native Python endpoints and dependency wiring.

### Legacy compatibility

Characterization/golden tests compare migrated behavior with legacy inputs/outputs where compatibility matters.

### Migration

Test representative legacy rows, nullability/type edge cases, idempotency and rollback/recovery requirements.

## 15. Non-goals for the first milestone

The first milestone will not:

- port all bundled applications,
- reproduce the entire Smarty/template stack,
- recreate the legacy installer/updater,
- implement every OAuth provider,
- recreate arbitrary PHP plugin loading,
- redesign the Webasyst database schema,
- expose SQLAlchemy as an application API.

## 16. Completion criteria for architecture foundation

The foundation is accepted when:

- application services run in unit tests with no FastAPI and no SQLAlchemy imports,
- repository/UoW fakes can replace persistence through constructor injection,
- MySQL/MariaDB connection can be selected by settings and composed at startup,
- switching a test adapter does not change application code,
- Pydantic contracts are the only data objects crossing presentation/application and application/persistence boundaries,
- SQLAlchemy ORM classes remain infrastructure-private,
- the contact vertical slice passes unit, persistence-contract and integration tests,
- important new architectural decisions are reflected in `AGENTS.md`.
