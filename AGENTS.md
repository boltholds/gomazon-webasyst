# AGENTS.md

## Purpose

This repository is the Python rewrite target for Webasyst Framework 4.2.0 and the applications shipped with the migration source.

The migration goal is behavioral compatibility where it matters, while replacing the PHP framework internals with a typed, testable Python architecture.

This file is the canonical architecture record for the rewrite. Agents MUST update it whenever they introduce or change an architectural boundary, dependency direction, public contract, persistence abstraction, compatibility rule, migration strategy, or cross-cutting subsystem.

Do not leave important architecture decisions only in chat, PR descriptions, issues, or implementation comments.

---

## Migration source inventory

The supplied Webasyst 4.2.0 archive contains the legacy framework and applications. The archive itself is not yet assumed to be committed to this repository.

Observed top-level legacy areas include:

- `wa-system/` — framework runtime and core infrastructure.
- `wa-apps/` — bundled applications.
- `wa-config/` — framework configuration.
- `wa-content/` — shared assets/content.
- `wa-installer/` — installer/update infrastructure.
- `wa-plugins/` — plugins.
- `wa-widgets/` — widgets.
- entry points including `index.php`, `api.php`, `cli.php`, `install.php`, and `wa.php`.

Observed bundled applications include:

- `apiexplorer`
- `blog`
- `developer`
- `dummy`
- `installer`
- `photos`
- `site`
- `team`
- `ui`

The rewrite MUST be driven by observed legacy behavior and compatibility tests rather than by mechanical PHP-to-Python translation.

---

## Core architectural decisions

### ADR-001 — Python application stack

Target runtime:

- Python 3.12+
- FastAPI / Starlette for HTTP and ASGI integration
- Pydantic v2 for explicit contracts
- `pydantic-settings` for application configuration
- SQLAlchemy 2.x as the first relational persistence adapter
- Alembic for schema migrations owned by the Python implementation
- pytest for automated tests

FastAPI is a presentation adapter. FastAPI-specific primitives MUST NOT become application- or domain-layer dependencies.

### ADR-002 — Database replaceability is a hard requirement

Business logic MUST NOT depend on a concrete database, SQLAlchemy session, SQLAlchemy model, SQL dialect, or database driver.

Database implementations are selected and assembled through dependency injection at the composition root.

Initial compatibility is expected to target the existing Webasyst relational schema, with MySQL/MariaDB as the first practical backend. The design MUST allow another relational backend, such as PostgreSQL, to be introduced without rewriting application services.

Database replacement means replacing infrastructure adapters, not modifying use cases.

### ADR-003 — Pydantic contracts are explicit boundaries

Pydantic v2 models are the canonical typed contracts used at architectural boundaries.

Use separate models when semantics differ, for example:

- `ContactCreate`
- `ContactUpdate`
- `ContactRead`
- `ContactFilter`

Do not reuse one giant model for create/update/read/database concerns.

Pydantic contracts MUST NOT contain persistence operations or depend on SQLAlchemy.

ORM instances MUST NOT cross the persistence boundary.

### ADR-004 — Dependency injection uses interfaces, not globals

Dependencies are passed explicitly, preferably through constructor injection.

Repository and infrastructure contracts should use `typing.Protocol` where practical.

FastAPI `Depends` may be used in the presentation/composition layer, but application services MUST remain directly constructible in tests without FastAPI.

No module-level mutable service locator, global database session, or hidden singleton dependency is allowed.

### ADR-005 — Repository + Unit of Work boundary

Persistence is accessed through repository contracts and an explicit Unit of Work abstraction.

Representative shape:

```python
from typing import Protocol

class ContactRepository(Protocol):
    async def get(self, contact_id: int) -> "ContactRead | None": ...
    async def create(self, data: "ContactCreate") -> "ContactRead": ...

class UnitOfWork(Protocol):
    contacts: ContactRepository

    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
```

Exact contracts may evolve, but the dependency direction may not be inverted: application code owns the interface; infrastructure implements it.

Transaction boundaries belong to application use cases through the Unit of Work abstraction. Do not pass `AsyncSession` or engine objects into use cases.

### ADR-006 — SQLAlchemy is an infrastructure detail

SQLAlchemy models live only inside the SQLAlchemy persistence adapter.

Preferred separation:

```text
Pydantic contract
      ^
      |
Application service -> Repository Protocol
                            ^
                            |
                  SQLAlchemy Repository
                            |
                      ORM models
                            |
                         Database
```

Do not make SQLAlchemy declarative models the canonical models for the whole application.

Database-specific SQL, indexes, locking behavior, extensions, and dialect workarounds MUST remain isolated inside infrastructure packages.

### ADR-007 — Compatibility is implemented through adapters

Legacy Webasyst behavior must not leak through the new codebase as arbitrary `wa*` conventions.

When compatibility is necessary, implement it in explicit compatibility adapters that translate legacy inputs and outputs into Python contracts.

Examples include:

- legacy URL and route resolution
- request parameter conventions
- authentication/session compatibility
- legacy API response envelopes
- legacy identifiers and field names
- plugin/hook/event translation
- configuration translation

New application code should consume typed contracts, not legacy associative-array semantics.

### ADR-008 — Preserve existing data before redesigning schema

The first migration target should read and write the existing Webasyst data safely where feasible.

Avoid destructive schema redesign during behavioral migration.

Any schema migration that changes legacy data shape must be:

1. justified in this file,
2. reversible or accompanied by an explicit irreversible migration plan,
3. covered by migration tests,
4. evaluated for coexistence with the legacy PHP system if dual-running is still required.

### ADR-009 — Migration is incremental

Do not attempt a blind one-shot rewrite of the entire framework.

Preferred order:

1. Characterize legacy behavior with tests and fixtures.
2. Establish Python project skeleton and composition root.
3. Implement configuration and dependency wiring.
4. Implement persistence abstractions and the first SQLAlchemy adapter.
5. Port routing/request/response compatibility.
6. Port contacts/users, authentication, sessions, permissions, and tokens.
7. Port API infrastructure.
8. Port event/hook/plugin boundaries.
9. Port CLI/background/installer concerns as required.
10. Port bundled applications one vertical slice at a time.
11. Replace legacy rendering/template behavior incrementally instead of coupling it to core migration.

Each migrated vertical slice should be usable and testable independently.

---

## Target dependency direction

The intended dependency flow is:

```text
presentation
    |
    v
application
    |
    v
contracts / domain abstractions
    ^
    |
infrastructure adapters
```

Infrastructure depends on application-owned abstractions; application code does not depend on infrastructure implementations.

A more concrete request path is:

```text
HTTP request
    |
FastAPI route / compatibility adapter
    |
Pydantic input contract
    |
Application use case/service
    |
Repository / UnitOfWork Protocol
    |
Selected persistence adapter
    |
Database
```

Response path:

```text
Database row
    |
Persistence adapter
    |
Pydantic/domain contract
    |
Application result
    |
Presentation/compatibility serializer
    |
HTTP response
```

---

## Suggested package layout

The exact names can evolve, but package boundaries should preserve the dependency rules above.

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
      permissions.py
      routing.py
      api.py

    application/
      services/
      commands/
      queries/
      ports/
        repositories.py
        unit_of_work.py
        cache.py
        filesystem.py
        events.py

    domain/
      contacts/
      auth/
      permissions/
      routing/
      plugins/

    infrastructure/
      persistence/
        sqlalchemy/
          models/
          repositories/
          unit_of_work.py
          mappings.py
      cache/
      filesystem/
      oauth/
      events/
      plugins/
      legacy/

    presentation/
      http/
        api/
        web/
        dependencies.py
      cli/

    compatibility/
      webasyst/
        routing/
        auth/
        api/
        config/
        plugins/

tests/
  unit/
  integration/
  compatibility/
  migration/
```

Avoid horizontal layers that become dumping grounds. Prefer feature-local modules when a subsystem becomes large, while retaining the same dependency direction.

---

## Contracts policy

Pydantic contracts should be small, explicit, and versionable.

Rules:

- Validate at system boundaries.
- Use strict types where silent coercion would hide legacy-data errors.
- Keep external/legacy field aliases explicit.
- Prefer `model_validate(..., from_attributes=True)` only at controlled adapter boundaries.
- Do not expose SQLAlchemy models directly through FastAPI response models.
- Do not put repository calls, HTTP calls, or side effects inside validators.
- Contract changes that affect public API compatibility must be documented in this file.
- Public API contracts require compatibility tests.

---

## Persistence policy

The application must remain database-agnostic.

Rules:

- Repositories expose intent-oriented operations, not arbitrary query-builder access.
- Do not expose SQLAlchemy `Select`, `Query`, `Session`, `AsyncSession`, `Engine`, rows, or ORM entities outside infrastructure.
- Keep dialect-specific behavior behind adapter interfaces.
- Avoid relying on MySQL-specific behavior in application code.
- Use explicit transaction scopes.
- A use case should be testable with an in-memory/fake repository and Unit of Work.
- Integration tests must run against the real first persistence adapter as well.
- When supporting multiple relational databases, add persistence contract tests that every adapter must pass.

Configuration should allow persistence selection without editing business code. Conceptually:

```text
DATABASE_BACKEND=sqlalchemy
DATABASE_URL=mysql+asyncmy://...
```

or:

```text
DATABASE_BACKEND=sqlalchemy
DATABASE_URL=postgresql+asyncpg://...
```

The exact supported drivers are implementation decisions and must be recorded here when introduced.

---

## Composition root

All concrete infrastructure selection happens at startup.

The composition root is responsible for constructing:

- settings
- database engine/adapter
- Unit of Work factory
- repositories
- cache adapter
- filesystem/storage adapter
- auth/OAuth adapters
- plugin/event adapters
- application services
- presentation dependencies

Application modules must not import a global container to fetch dependencies dynamically.

---

## Web/API compatibility policy

Compatibility should be deliberate and measurable.

For migrated endpoints, record and test as applicable:

- HTTP method
- path
- query/form/body parsing behavior
- authentication requirements
- authorization rules
- response status
- response JSON shape or rendered result
- redirects
- cookies/session effects
- error semantics

When exact compatibility is intentionally broken, document the decision here before treating the new behavior as canonical.

---

## Authentication and authorization

Auth is a cross-cutting subsystem and must remain separated from transport and persistence details.

Expected abstractions include concepts such as:

- user/contact identity
- session
- OAuth client
- access token
- group/role membership
- permission/capability checks

Permission decisions belong in application/domain policy, while token parsing, cookie parsing, storage, and cryptographic/provider integrations belong in adapters.

Do not make authorization depend directly on FastAPI route objects or SQLAlchemy queries.

---

## Plugins, hooks, and events

Legacy Webasyst is extensible, so plugin compatibility must be treated as an explicit subsystem.

Do not reproduce PHP dynamic loading semantics throughout the Python codebase.

Use typed plugin/event interfaces and translate legacy hook names/payloads at the compatibility boundary.

If a legacy hook cannot be preserved exactly, document:

- the legacy hook,
- the new event/extension point,
- payload mapping,
- ordering guarantees,
- error isolation behavior.

---

## Rendering and frontend migration

Frontend migration is decoupled from backend migration where possible.

Existing JS/CSS/assets may be preserved while backend behavior is ported.

Do not make core services depend on a template engine.

Template-engine choice and Smarty-to-Python migration must remain a presentation-layer concern. A future rendering decision should be recorded here before broad template conversion begins.

---

## Testing strategy

### Unit tests

Use fakes/stubs for repositories, Unit of Work, cache, filesystem, external APIs, and event buses.

Application use cases must be testable without a running web server or database.

### Persistence contract tests

Define reusable behavioral tests for repository contracts. Run them against every concrete persistence adapter.

### Integration tests

Cover:

- SQLAlchemy mappings and queries
- transactions and rollback
- constraints
- auth/session persistence
- route wiring
- middleware
- external adapter boundaries

### Legacy compatibility tests

Before porting important legacy behavior, capture representative inputs and outputs from Webasyst where possible.

Use golden/characterization tests for public behavior rather than copying implementation details.

### Migration tests

Any data migration must test representative legacy rows, edge cases, rollback/recovery expectations, and idempotency where applicable.

---

## Agent implementation rules

1. Read this file before changing architecture or adding a subsystem.
2. Preserve dependency direction.
3. Do not bypass DI with globals for convenience.
4. Do not leak ORM models outside persistence adapters.
5. Use Pydantic v2 contracts at explicit boundaries.
6. Add/adjust Protocols before coupling application services to infrastructure.
7. Add tests before or with behavior-changing implementation.
8. Prefer vertical, reviewable migration slices.
9. Do not translate PHP mechanically when the behavior can be represented more clearly in Python.
10. Preserve legacy behavior only when it is a compatibility requirement; do not preserve incidental PHP structure.
11. Update this `AGENTS.md` in the same change whenever an architectural decision changes.
12. Add a new ADR entry below for every significant new architectural decision. Do not silently rewrite history; supersede earlier ADRs when necessary.

---

## Architecture decision log

Use entries of this form:

```text
### ADR-NNN — Title
Status: accepted | proposed | superseded
Date: YYYY-MM-DD

Context:
...

Decision:
...

Consequences:
...
```

Current decisions ADR-001 through ADR-009 above are accepted as the initial migration baseline.

---

## Immediate migration baseline

The first implementation milestone should prove the architecture with one thin vertical slice rather than attempting broad framework parity.

That slice should demonstrate:

- application startup,
- settings,
- DI/composition root,
- Pydantic request/response contracts,
- repository Protocol,
- Unit of Work Protocol,
- SQLAlchemy implementation,
- connection to a Webasyst-compatible relational database,
- one read/write use case,
- FastAPI endpoint,
- unit tests with fakes,
- integration tests with the concrete persistence adapter.

Only after this boundary is proven should migration expand into framework-wide auth, routing, plugin, and application compatibility.
