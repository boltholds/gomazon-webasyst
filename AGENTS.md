# AGENTS.md

## Purpose

This repository is the Python rewrite target for Webasyst Framework 4.2.0 and the product built on top of it.

The migration goal is behavioral compatibility where it matters while replacing PHP framework internals with a typed, testable Python architecture.

This file is the canonical architecture record. Agents MUST update it in the same change whenever they introduce or change an architectural boundary, dependency direction, public contract, persistence abstraction, compatibility rule, migration strategy, or cross-cutting subsystem.

Do not leave important architectural decisions only in chat, PR descriptions, issues, code comments, design docs, or implementation plans.

Authoritative companion artifacts:

- Design: `docs/superpowers/specs/2026-09-14-webasyst-python-rewrite-design.md`
- First implementation plan: `docs/superpowers/plans/2026-09-14-contacts-foundation.md`

---

## Legacy source inventory

The supplied Webasyst 4.2.0 archive contains 7,569 files, including 2,468 PHP files.

Important areas:

- `wa-system/` — framework runtime and shared infrastructure.
- `wa-apps/` — bundled applications.
- `wa-content/` — shared assets/content.
- `wa-plugins/` — plugins.
- `wa-widgets/` — widgets.
- `wa-installer/` — installer/update infrastructure.
- `wa-config/` — framework configuration.
- entry points: `index.php`, `api.php`, `cli.php`, `wa.php`, `install.php`.

Important legacy framework surfaces:

- `waSystem` — runtime/service locator, factories, dispatch, configuration, user state, plugins/events.
- `waRouting` — domain/path routing and URL generation.
- `waModel` and `waDb*` — CRUD/query execution, metadata, transactions and database adapters.
- `waFrontController`, `waController`, `waAction` — HTTP dispatch/controller execution.
- `waAPIController`, `waAPIMethod` — API dispatch, access checks and token handling.
- `waAuth`, `waOAuth2Adapter` — authentication and OAuth providers.
- `waEvent` — event discovery and dispatch.
- `waPlugin` / `waPlugins` — plugin lifecycle, routing, cron, settings, templates/assets.

The rewrite MUST be driven by observed behavior and compatibility tests, not mechanical PHP-to-Python translation.

---

## Accepted architecture decisions

### ADR-001 — Python stack
Status: accepted
Date: 2026-09-14

Use Python 3.12+, FastAPI/Starlette, Pydantic v2, `pydantic-settings`, SQLAlchemy 2.x as the first relational persistence adapter, Alembic for Python-owned schema migrations, and pytest.

FastAPI is a presentation adapter. FastAPI types must not become application/domain dependencies.

### ADR-002 — Database replaceability is a hard requirement
Status: accepted
Date: 2026-09-14

Business logic MUST NOT depend on a concrete database, SQLAlchemy session/model, SQL dialect, or driver.

Persistence implementations are selected through dependency injection at the composition root. MySQL/MariaDB and the existing Webasyst schema are the first compatibility target. PostgreSQL or another backend must be introducible without rewriting application use cases.

Database replacement means replacing configuration/infrastructure adapters, not modifying business logic.

### ADR-003 — Pydantic v2 contracts define boundaries
Status: accepted
Date: 2026-09-14

Pydantic v2 models are the canonical typed data contracts crossing architectural boundaries.

Use separate models by semantics, e.g. `ContactCreate`, `ContactUpdate`, `ContactRead`, `ContactFilter`.

Rules:

- no persistence operations in Pydantic models,
- no SQLAlchemy dependency in contracts,
- no hidden I/O in validators,
- explicit aliases for legacy field names when needed,
- strict validation where silent legacy coercion would hide errors,
- public API contract changes require compatibility tests,
- ORM instances MUST NOT cross the persistence boundary.

### ADR-004 — DI uses explicit interfaces, not globals
Status: accepted
Date: 2026-09-14

Prefer constructor injection. Application-owned infrastructure boundaries use `typing.Protocol` where practical.

FastAPI `Depends` is permitted only in presentation/composition wiring. Application services must remain directly constructible in tests.

Forbidden:

- global mutable service locator,
- global DB session,
- hidden singleton dependencies,
- recreating `waSystem::getInstance()` as a Python global container.

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
    async def update(self, contact_id: int, data: "ContactUpdate") -> "ContactRead | None": ...

class UnitOfWork(Protocol):
    contacts: ContactRepository
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...

class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...
```

Exact repository methods evolve from use-case needs. Do not expose generic query builders as repository APIs. Never pass SQLAlchemy `Session`/`AsyncSession` into application use cases.

### ADR-006 — SQLAlchemy is infrastructure-private
Status: accepted
Date: 2026-09-14

SQLAlchemy models and primitives live under the SQLAlchemy persistence adapter. SQLAlchemy may be referenced by the composition root solely to construct/own concrete resources.

The following must not enter contracts/application/presentation handler signatures:

- ORM declarative classes,
- `Session` / `AsyncSession`,
- `Engine` / `AsyncEngine`,
- SQLAlchemy statements/results,
- dialect-specific SQL.

SQLAlchemy multi-dialect support does not replace the repository/UoW abstraction.

### ADR-007 — Legacy compatibility lives in adapters
Status: accepted
Date: 2026-09-14

Webasyst-specific behavior is translated at explicit compatibility boundaries rather than spread through new application code.

Compatibility adapters cover as needed:

- domain/path route resolution,
- request parameter conventions,
- auth/session behavior,
- API response/error envelopes,
- legacy identifiers and field names,
- plugin/hook/event naming,
- configuration translation.

New application code consumes typed contracts, not PHP associative-array semantics.

### ADR-008 — Preserve existing data before redesigning schema
Status: accepted
Date: 2026-09-14

Initial migration reads/writes the existing Webasyst data safely where feasible. Do not perform destructive schema redesign during behavioral migration.

Any legacy data-shape change must be documented here, covered by migration tests, and include rollback/recovery/coexistence implications.

Alembic owns only schema changes introduced by the Python system; it must not blindly recreate the existing legacy schema.

### ADR-009 — Migration is incremental
Status: accepted
Date: 2026-09-14

Migrate in vertical, independently testable slices.

Broad sequence:

1. characterization tests/fixtures,
2. packaging/composition root,
3. persistence ports + first adapter,
4. contact vertical slice,
5. routing/dispatch compatibility,
6. users/auth/sessions/permissions/tokens,
7. API compatibility,
8. events/hooks/plugins,
9. CLI/background/installer concerns as needed,
10. bundled applications by product priority,
11. rendering/template replacement independently from core migration.

### ADR-010 — First architectural proof is the contact vertical slice
Status: accepted
Date: 2026-09-14

Contacts/users are foundational to Webasyst authentication and permissions, so contacts prove the first architectural seams.

The slice includes startup/settings, composition root, Pydantic contact contracts, repository/UoW protocols, SQLAlchemy adapter, read/create/update use cases, thin FastAPI endpoints, fake-based unit tests, persistence-contract tests, and concrete adapter integration tests.

This proves architecture only. It is not Webasyst contact API parity until legacy behavior is separately characterized and handled by compatibility adapters.

### ADR-011 — `waSystem` will not be recreated as a universal runtime object
Status: accepted
Date: 2026-09-14

Responsibilities concentrated in `waSystem` are split between composition root, settings, request-scoped context, routing adapters, application services, infrastructure ports/adapters, and plugin/event registries.

No universal runtime/service-locator object may become a hidden dependency of the application.

### ADR-012 — First contact slice maps only `wa_contact`
Status: accepted
Date: 2026-09-14

The first contacts vertical slice maps the base legacy `wa_contact` table only.

The source schema for this table includes profile fields plus legacy user/auth-related columns. The first public contact contract exposes profile fields only. Password/session/token behavior is not exposed by this slice.

`wa_contact_emails`, `wa_contact_data`, and `wa_contact_data_text` are separate later compatibility slices. This prevents profile CRUD from being prematurely coupled to email state, arbitrary contact fields, or authentication.

### ADR-013 — Initial relational persistence path is async
Status: accepted
Date: 2026-09-14

The first SQLAlchemy implementation uses `AsyncEngine`, `AsyncSession`, async repositories, and an async Unit of Work.

MySQL/MariaDB uses `asyncmy`. Fast persistence-contract/integration tests may use `aiosqlite` without changing application code.

Async SQLAlchemy and driver primitives remain infrastructure-private.

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
Application use case
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
src/gomazon_webasyst/
  main.py
  composition/
    settings.py
    container.py
  contracts/
    contacts.py
    auth.py
    routing.py
    permissions.py
    api.py
    plugins.py
  application/
    contacts.py
    errors.py
    ports/
      contacts.py
      unit_of_work.py
      auth.py
      cache.py
      filesystem.py
      events.py
      plugins.py
  infrastructure/
    persistence/
      sqlalchemy/
        base.py
        models.py
        mappings.py
        repositories.py
        unit_of_work.py
        factory.py
    auth/
    cache/
    filesystem/
    events/
    plugins/
  compatibility/webasyst/
    routing/
    auth/
    api/
    config/
    plugins/
  presentation/
    http/
    cli/

tests/
  architecture/
  unit/
  persistence_contracts/
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

The composition root constructs and owns settings, persistence resources, UoW factory, repositories, cache/filesystem adapters, auth/OAuth adapters, event/plugin adapters, and application services.

Application modules must never import a global container to resolve dependencies dynamically.

---

## Persistence rules

- Repositories expose intent-oriented methods.
- No arbitrary query-builder access outside infrastructure.
- No MySQL-specific assumptions in application code.
- Database-specific indexes, locks, extensions and SQL remain inside adapters.
- Use explicit transaction scopes.
- Every use case must be testable with fake repositories/UoW.
- Concrete persistence adapters require integration tests.
- Multiple adapters must pass the same persistence contract suite.
- Existing legacy tables are mapped; Python migrations do not recreate them blindly.

Initial selection examples:

```text
GOMAZON_DATABASE_URL=mysql+asyncmy://user:pass@host/webasyst
```

Tests may use:

```text
GOMAZON_DATABASE_URL=sqlite+aiosqlite:///:memory:
```

A future PostgreSQL implementation may use a different infrastructure adapter/driver without changing application contracts/use cases.

---

## Contact foundation scope

The first native Python contact endpoints are architectural proof endpoints, not legacy Webasyst API compatibility endpoints.

Initial public profile fields come from `wa_contact` and include:

- `id`, `name`,
- `firstname`, `middlename`, `lastname`,
- `title`, `company`, `jobtitle`,
- `company_contact_id`, `is_company`,
- `locale`, `timezone`,
- `create_datetime` on reads.

The following remain out of the first public contract even though some are stored on `wa_contact`:

- `login`, `password`, `is_user`, `is_staff`,
- auth/session/token behavior,
- email/phone/custom contact fields,
- photo/file handling,
- birthday/sex/about compatibility semantics.

Those capabilities get dedicated contracts/use cases when migrated.

---

## Web/API compatibility policy

For every migrated compatibility surface, characterize/test as applicable: method, route/domain matching, parsing, auth, authorization, status, output shape, redirects, cookies/session mutation, and errors.

When exact compatibility is intentionally broken, record an ADR before the new behavior becomes canonical.

---

## Authentication and authorization

Expected abstractions include contact/user identity, session, OAuth client/provider, access token/auth code, group/role membership, and permission/capability checks.

Permission decisions belong in application/domain policy. Cookie/token parsing, crypto/provider HTTP mechanics and persistence belong in adapters.

Authorization must not depend directly on FastAPI route objects or SQLAlchemy queries.

---

## Plugins, hooks and events

Do not reproduce arbitrary PHP dynamic loading throughout Python code.

Use typed plugin/event interfaces and translate legacy hook names/payloads at compatibility boundaries.

For an incompatible legacy hook, document its legacy name, new extension point, payload mapping, ordering guarantees, and error-isolation behavior.

---

## Rendering/frontend

Frontend migration is decoupled from backend migration where possible. Existing JS/CSS/assets may remain while backend behavior is ported.

Core/application services must not depend on a template engine. Broad Smarty/template conversion requires a separate ADR.

---

## Error model

Application errors are framework-agnostic typed errors/results.

Presentation adapters translate them to native HTTP responses. Webasyst compatibility adapters may translate the same errors to legacy envelopes.

Raw SQLAlchemy/driver exceptions must not leak across the persistence boundary.

---

## Testing strategy

### Unit
Use fake repositories/UoW and fake external ports. No DB or ASGI server is required for application-use-case tests.

### Architecture
Automated import-boundary tests prevent FastAPI/SQLAlchemy/DB drivers from leaking into contracts/application.

### Persistence contract
Reusable behavioral tests define repository expectations and run against each concrete adapter.

### Integration
Cover mappings, queries, transactions, concrete DI wiring, configured dialect selection, and ASGI routes.

### Legacy compatibility
Use characterization/golden tests for behavior claimed to match Webasyst.

### Migration
Cover representative legacy rows, type/nullability edge cases, idempotency, rollback/recovery, and coexistence where applicable.

---

## Agent implementation rules

1. Read this file before changing architecture or adding a subsystem.
2. Read the relevant accepted design spec and implementation plan.
3. Preserve dependency direction.
4. Do not bypass DI with globals.
5. Do not leak ORM models, sessions, engines, statements, or driver types into application contracts/use cases.
6. Use Pydantic v2 contracts at explicit boundaries.
7. Add/adjust application-owned Protocols before coupling services to infrastructure.
8. Add tests before or with behavior-changing implementation.
9. Prefer small vertical migration slices.
10. Do not mechanically translate PHP structure.
11. Preserve legacy behavior only when it is a compatibility requirement.
12. Update this file in the same change whenever architecture changes.
13. Add or supersede a numbered ADR; do not silently rewrite architectural history.
14. Do not claim Webasyst compatibility without characterization/compatibility tests.
15. Native Python endpoints and compatibility endpoints must remain distinguishable until parity is proven.

---

## Foundation completion criteria

The initial foundation is proven when:

- application use cases run without FastAPI/SQLAlchemy imports,
- persistence can be replaced with fakes through DI,
- MySQL/MariaDB can be selected/configured at the composition root,
- changing a test adapter does not modify application code,
- Pydantic contracts cross presentation/application and application/persistence boundaries,
- ORM models remain infrastructure-private,
- the `wa_contact` vertical slice passes unit, architecture, persistence-contract, integration, and HTTP tests,
- every introduced architectural decision is reflected in this file.
