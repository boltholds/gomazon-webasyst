# AGENTS.md

## Purpose

This repository is the Python rewrite target for Webasyst Framework 4.2.0 and the product built on top of it.

The migration goal is behavioral compatibility where it matters, while replacing PHP framework internals with a typed, testable Python architecture.

This file is the canonical architecture record. Agents MUST update it whenever they introduce or change an architectural boundary, dependency direction, public contract, persistence abstraction, compatibility rule, migration strategy, or cross-cutting subsystem.

Do not leave important architectural decisions only in chat, PR descriptions, issues, implementation comments, or separate design documents.

Detailed design baseline: `docs/superpowers/specs/2026-09-14-webasyst-python-rewrite-design.md`.

---

## Legacy source inventory

The supplied Webasyst 4.2.0 archive contains 7,569 files, including 2,468 PHP files.

Important areas:

- `wa-system/` — 1,574 files; framework runtime and shared infrastructure.
- `wa-apps/` — 4,232 files; bundled applications.
- `wa-content/` — 1,028 files.
- `wa-plugins/` — 584 files.
- `wa-widgets/` — 114 files.
- `wa-installer/` — installer bootstrap/update infrastructure.
- `wa-config/` — framework configuration.
- entry points: `index.php`, `api.php`, `cli.php`, `wa.php`, `install.php`.

Largest bundled applications observed:

- `site` — 1,345 files.
- `developer` — 975 files.
- `blog` — 584 files.
- `photos` — 567 files.
- `team` — 413 files.
- `installer` — 157 files.
- `ui` — 113 files.
- `apiexplorer` — 60 files.
- `dummy` — 17 files.

Important legacy framework surfaces:

- `waSystem` — runtime/service locator, factories, dispatch, configuration, user state, plugins/events.
- `waRouting` — domain/path routing and URL generation.
- `waModel` and `waDb*` — CRUD/query execution, metadata, transactions and DB adapters.
- `waFrontController`, `waController`, `waAction` — HTTP dispatch/controller execution.
- `waAPIController`, `waAPIMethod` — API dispatch, access checks and token handling.
- `waAuth`, `waOAuth2Adapter` — authentication and OAuth providers.
- `waEvent` — event discovery and dispatch.
- `waPlugin` / `waPlugins` — plugin lifecycle, routing, cron, settings and templates/assets.

The rewrite MUST be driven by observed legacy behavior and compatibility tests, not mechanical PHP-to-Python translation.

---

## Accepted architecture decisions

### ADR-001 — Python stack
Status: accepted
Date: 2026-09-14

Use:

- Python 3.12+
- FastAPI / Starlette
- Pydantic v2
- `pydantic-settings`
- SQLAlchemy 2.x as the first relational persistence adapter
- Alembic for Python-owned schema migrations
- pytest

FastAPI is a presentation adapter. FastAPI types must not become application/domain dependencies.

### ADR-002 — Database replaceability is a hard requirement
Status: accepted
Date: 2026-09-14

Business logic MUST NOT depend on a concrete database, SQLAlchemy session/model, SQL dialect, or driver.

Persistence implementations are selected through dependency injection at the composition root.

MySQL/MariaDB and the existing Webasyst schema are the first compatibility target. PostgreSQL or another backend must be introducible without rewriting application use cases.

Database replacement means replacing infrastructure adapters, not modifying business logic.

### ADR-003 — Pydantic v2 contracts define boundaries
Status: accepted
Date: 2026-09-14

Pydantic v2 models are the canonical typed contracts crossing architectural boundaries.

Separate models by semantics, for example:

- `ContactCreate`
- `ContactUpdate`
- `ContactRead`
- `ContactFilter`

Rules:

- no persistence operations in Pydantic models,
- no SQLAlchemy dependency in contracts,
- no hidden I/O in validators,
- use explicit aliases for legacy field names,
- use strict types where silent legacy coercion would hide errors,
- public API contract changes require compatibility tests.

ORM instances MUST NOT cross the persistence boundary.

### ADR-004 — DI uses explicit interfaces, not globals
Status: accepted
Date: 2026-09-14

Prefer constructor injection.

Application-owned infrastructure boundaries should use `typing.Protocol` where practical.

FastAPI `Depends` is permitted only in presentation/composition wiring. Application services must remain directly constructible in tests.

Forbidden:

- global mutable service locator,
- global DB session,
- hidden singleton dependencies,
- recreating `waSystem::getInstance()` semantics as a Python global container.

### ADR-005 — Repository + Unit of Work persistence boundary
Status: accepted
Date: 2026-09-14

Application code owns repository and Unit of Work protocols.

Representative shape:

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

Exact methods evolve from use-case needs. Do not expose generic query builders as repository APIs.

Transaction boundaries are controlled through Unit of Work. Never pass SQLAlchemy `Session`/`AsyncSession` into application use cases.

### ADR-006 — SQLAlchemy is infrastructure-private
Status: accepted
Date: 2026-09-14

SQLAlchemy models and primitives live only under the SQLAlchemy persistence adapter.

The intended seam is:

```text
Application service
      |
Repository/UoW Protocol
      ^
      |
SQLAlchemy adapter
      |
ORM models
      |
Database
```

The following must not escape infrastructure:

- ORM declarative classes,
- `Session` / `AsyncSession`,
- `Engine` / `AsyncEngine`,
- SQLAlchemy statements/results,
- dialect-specific SQL.

SQLAlchemy multi-dialect support does not replace the repository/UoW abstraction.

### ADR-007 — Legacy compatibility lives in adapters
Status: accepted
Date: 2026-09-14

Webasyst-specific behavior must be translated at explicit compatibility boundaries rather than spread through new application code.

Compatibility adapters cover, as needed:

- domain/path route resolution,
- request parameter conventions,
- auth/session behavior,
- API response/error envelopes,
- legacy identifiers and field names,
- plugin/hook/event naming,
- configuration translation.

New application code consumes Pydantic contracts, not PHP associative-array semantics.

### ADR-008 — Preserve existing data before redesigning schema
Status: accepted
Date: 2026-09-14

Initial migration should read/write the existing Webasyst data safely where feasible.

Do not perform destructive schema redesign during behavioral migration.

Any legacy data-shape change must be documented here, covered by migration tests, and include rollback/recovery/coexistence implications.

Alembic owns schema changes introduced by the Python system; it must not blindly recreate the existing legacy schema.

### ADR-009 — Migration is incremental
Status: accepted
Date: 2026-09-14

Migrate in vertical, independently testable slices.

Broad sequence:

1. characterization tests/fixtures for legacy behavior,
2. Python packaging and composition root,
3. persistence ports + first adapter,
4. contact vertical slice,
5. routing/dispatch compatibility,
6. users/auth/sessions/permissions/tokens,
7. API compatibility,
8. events/hooks/plugins,
9. CLI/background/installer concerns as required,
10. bundled applications by product priority,
11. rendering/template replacement independently from core migration.

### ADR-010 — First architectural proof is the contact vertical slice
Status: accepted
Date: 2026-09-14

Contacts/users are foundational to Webasyst authentication and permissions, so the first implementation slice will use contacts to prove all architectural seams.

The slice must include:

- project startup and settings,
- composition root,
- `ContactCreate`, `ContactUpdate`, `ContactRead` Pydantic contracts,
- `ContactRepository` protocol,
- `UnitOfWork` and `UnitOfWorkFactory` protocols,
- SQLAlchemy adapter mapped to relevant legacy contact tables,
- one read use case,
- one write/update use case,
- thin FastAPI endpoints,
- unit tests using fakes,
- persistence contract tests,
- integration tests for the concrete adapter.

This slice proves architecture only. It is not considered Webasyst contact API parity until legacy behavior is separately characterized and handled by a compatibility adapter.

### ADR-011 — `waSystem` will not be recreated as a universal runtime object
Status: accepted
Date: 2026-09-14

The responsibilities currently concentrated in `waSystem` are split between:

- composition root,
- settings,
- request-scoped context,
- routing adapters,
- application services,
- infrastructure ports/adapters,
- plugin/event registries.

No new universal runtime/service-locator object may become the hidden dependency of the application.

---

## Target dependency direction

```text
presentation / compatibility
          |
          v
      application
          |
          v
contracts + application-owned ports
          ^
          |
 infrastructure implementations
```

Concrete request path:

```text
HTTP request
    |
FastAPI route / Webasyst compatibility adapter
    |
Pydantic input contract
    |
Application command/query/service
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
Pydantic contract
    |
Application result
    |
Presentation/compatibility serializer
    |
HTTP response
```

---

## Target package layout

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

Feature-local packages may replace broad horizontal directories as subsystems grow, but dependency direction must remain intact.

---

## Legacy subsystem mapping

| Legacy | Python target |
|---|---|
| `waSystem` | composition root + settings + explicit services/request context |
| `waRouting` | native FastAPI routes + Webasyst compatibility route resolver |
| `waModel`, `waDb*` | repository/UoW ports + SQLAlchemy persistence adapter |
| `waFrontController`, `waController`, `waAction` | thin presentation/compatibility handlers + application use cases |
| `waAPIController`, `waAPIMethod` | typed API routers + auth dependency + compatibility serializer |
| `waAuth`, OAuth adapters | auth use cases + auth/session/token ports + provider adapters |
| `waEvent` | typed event bus + legacy event bridge |
| `waPlugin`, `waPlugins` | plugin manifest/registry + typed hooks + compatibility bridge |

Do not recreate generic legacy escape hatches such as `waModel::query()` as application-level APIs.

---

## Composition root

All concrete implementation selection occurs at startup.

The composition root constructs:

- settings,
- persistence implementation,
- engine/connection resources,
- Unit of Work factory,
- repositories,
- cache adapter,
- filesystem/storage adapter,
- auth/OAuth adapters,
- event/plugin adapters,
- application services,
- presentation dependencies.

Application modules must never import a global container to resolve dependencies dynamically.

---

## Persistence rules

- Repositories expose intent-oriented methods.
- No arbitrary query-builder access outside infrastructure.
- No MySQL-specific assumptions in application code.
- Database-specific indexes, locks, extensions and SQL remain inside adapters.
- Use explicit transaction scopes.
- Every application use case must be testable with fake/in-memory repositories and UoW.
- Concrete persistence adapters require integration tests.
- Multiple database adapters must pass the same persistence contract test suite.

Configuration must permit adapter/database selection without business-code edits, conceptually:

```text
DATABASE_BACKEND=sqlalchemy
DATABASE_URL=mysql+asyncmy://...
```

or:

```text
DATABASE_BACKEND=sqlalchemy
DATABASE_URL=postgresql+asyncpg://...
```

Supported drivers become explicit architecture decisions when implemented.

---

## Web/API compatibility policy

For every migrated compatibility surface, characterize and test as applicable:

- method,
- path/domain matching,
- input parsing,
- authentication,
- authorization,
- response status,
- response shape/rendered result,
- redirects,
- cookies/session mutation,
- error semantics.

When exact compatibility is intentionally broken, document it here before the new behavior becomes canonical.

---

## Authentication and authorization

Expected abstractions include:

- user/contact identity,
- session,
- OAuth client/provider,
- access token/auth code,
- group/role membership,
- permission/capability checks.

Permission decisions belong in application/domain policy. Cookie parsing, token parsing, crypto/provider HTTP mechanics and persistence belong in adapters.

Authorization must not depend directly on FastAPI route objects or SQLAlchemy queries.

---

## Plugins, hooks and events

Do not reproduce arbitrary PHP dynamic loading semantics throughout Python code.

Use typed plugin/event interfaces and translate legacy hook names/payloads at the compatibility boundary.

For any incompatible legacy hook, document:

- legacy hook name,
- new extension point,
- payload mapping,
- ordering guarantees,
- error isolation behavior.

---

## Rendering/frontend

Frontend migration is decoupled from backend migration where possible.

Existing JS/CSS/assets may remain while backend behavior is ported.

Core/application services must not depend on a template engine.

Smarty/template migration remains a presentation-layer concern and requires a separate ADR before broad conversion.

---

## Error model

Application errors are framework-agnostic typed errors/results.

Presentation adapters translate them to native HTTP responses. Webasyst compatibility adapters may translate the same errors to legacy envelopes.

Infrastructure exceptions must not leak raw SQLAlchemy/driver details across the persistence boundary.

---

## Testing strategy

### Unit

Use fake repositories/UoW and fake external ports. No running DB or ASGI server should be required for application-use-case tests.

### Persistence contract

Define reusable behavioral tests for repository contracts. Run them against each concrete adapter.

### Integration

Cover mappings, queries, transaction behavior, constraints and concrete DI wiring.

### HTTP

Test native endpoints at the ASGI boundary.

### Legacy compatibility

Use characterization/golden tests for behavior that must match Webasyst.

### Migration

Cover representative legacy rows, type/nullability edge cases, idempotency and rollback/recovery expectations.

---

## Agent implementation rules

1. Read this file before changing architecture or adding a subsystem.
2. Also read the accepted design spec under `docs/superpowers/specs/` when working on the rewrite foundation.
3. Preserve dependency direction.
4. Do not bypass DI with globals for convenience.
5. Do not leak ORM models or SQLAlchemy primitives outside persistence adapters.
6. Use Pydantic v2 contracts at explicit boundaries.
7. Add/adjust application-owned Protocols before coupling services to infrastructure.
8. Add tests before or with behavior-changing implementation.
9. Prefer small vertical migration slices.
10. Do not mechanically translate PHP implementation structure.
11. Preserve legacy behavior only when it is a compatibility requirement.
12. Update this `AGENTS.md` in the same change whenever an architectural decision changes.
13. Add/supersede an ADR here for every significant new architectural decision; do not silently rewrite architectural history.
14. Do not claim Webasyst compatibility without characterization/compatibility tests for the behavior in question.

---

## Architecture completion criteria for the foundation

The initial architecture is proven when:

- application services run in tests without FastAPI and without SQLAlchemy imports,
- persistence can be replaced with fakes through DI,
- MySQL/MariaDB can be selected/configured at the composition root,
- changing a test persistence adapter does not modify application code,
- Pydantic contracts cross presentation/application and application/persistence boundaries,
- ORM models remain infrastructure-private,
- the contact vertical slice passes unit, persistence-contract and integration tests,
- every newly introduced architectural decision is reflected in this file.
