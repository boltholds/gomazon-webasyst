# AGENTS.md

## Purpose

This repository is the Python rewrite target for Webasyst Framework 4.2.0 and the product built on top of it.

The migration goal is behavioral compatibility where it matters while replacing PHP framework internals with a typed, testable Python architecture.

This file is the canonical architecture record. Agents MUST update it in the same change whenever they introduce or change an architectural boundary, dependency direction, public contract, persistence abstraction, compatibility rule, migration strategy, or cross-cutting subsystem.

Do not leave important architectural decisions only in chat, PR descriptions, issues, code comments, design docs, or implementation plans.

Authoritative companion artifacts:

- Foundation design: `docs/superpowers/specs/2026-09-14-webasyst-python-rewrite-design.md`
- Contacts implementation plan: `docs/superpowers/plans/2026-09-14-contacts-foundation.md`
- Routing/dispatch design: `docs/superpowers/specs/2026-09-14-routing-dispatch-design.md`

Official legacy documentation reference: `https://developers.webasyst.com/docs`.

---

## Legacy source inventory

The supplied Webasyst 4.2.0 archive contains the framework runtime and bundled applications.

Important areas:

- `wa-system/` — framework runtime and shared infrastructure.
- `wa-apps/` — bundled applications.
- `wa-content/` — shared assets/content.
- `wa-plugins/` — plugins.
- `wa-widgets/` — widgets.
- `wa-installer/` — installer/update infrastructure.
- `wa-config/` — framework configuration.
- entry points: `index.php`, `api.php`, `cli.php`, `wa.php`, `install.php`.

Important framework surfaces:

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

Use separate models by semantics. Contracts contain no persistence operations, SQLAlchemy dependencies, or hidden I/O.

ORM instances MUST NOT cross the persistence boundary.

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

Application code owns repository and Unit of Work protocols. Repositories expose intent-oriented operations, not generic query builders. Use cases never receive SQLAlchemy sessions or engines.

### ADR-006 — SQLAlchemy is infrastructure-private
Status: accepted
Date: 2026-09-14

SQLAlchemy models and primitives live under the SQLAlchemy persistence adapter. The composition root may reference SQLAlchemy solely to construct/own concrete resources.

ORM classes, sessions, engines, statements/results, and dialect-specific SQL must not enter contracts/application/presentation handler signatures.

### ADR-007 — Legacy compatibility lives in adapters
Status: accepted
Date: 2026-09-14

Webasyst-specific behavior is translated at explicit compatibility boundaries rather than spread through new application code.

Compatibility adapters cover route/config parsing, request conventions, auth/session behavior, API envelopes, legacy field names, and plugin/hook/event naming.

New application code consumes typed contracts, not PHP associative-array semantics.

### ADR-008 — Preserve existing data before redesigning schema
Status: accepted
Date: 2026-09-14

Initial migration reads/writes the existing Webasyst data safely where feasible. Do not perform destructive schema redesign during behavioral migration.

Alembic owns only schema changes introduced by the Python system; it must not blindly recreate the existing legacy schema.

### ADR-009 — Migration is incremental
Status: accepted
Date: 2026-09-14

Migrate in vertical, independently testable slices:

1. characterization fixtures,
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

Contacts/users prove the first architectural seams: settings, composition root, Pydantic contracts, repository/UoW protocols, SQLAlchemy adapter, use cases, HTTP endpoints, and tests.

This proves architecture only. It is not Webasyst contact API parity until legacy behavior is separately characterized.

### ADR-011 — `waSystem` will not be recreated as a universal runtime object
Status: accepted
Date: 2026-09-14

Responsibilities concentrated in `waSystem` are split between composition root, settings, request-scoped context, routing adapters, application services, infrastructure ports/adapters, and plugin/event registries.

No universal runtime/service-locator object may become a hidden dependency of the application.

### ADR-012 — First contact slice maps only `wa_contact`
Status: accepted
Date: 2026-09-14

The first contacts vertical slice maps the base legacy `wa_contact` table only.

The first public contact contract exposes profile fields only. `wa_contact_emails`, `wa_contact_data`, `wa_contact_data_text`, passwords, sessions, and tokens are separate later slices.

### ADR-013 — Initial relational persistence path is async
Status: accepted
Date: 2026-09-14

The first SQLAlchemy implementation uses `AsyncEngine`, `AsyncSession`, async repositories, and an async Unit of Work.

MySQL/MariaDB uses `asyncmy`. Tests may use `aiosqlite` without changing application code. Async SQLAlchemy and driver primitives remain infrastructure-private.

### ADR-014 — Mutually exclusive states use discriminated unions, not nullable bags
Status: accepted
Date: 2026-09-14

Nullable/optional fields MUST NOT be used to encode mutually exclusive architectural states.

Use Pydantic discriminated unions and normalize legacy input at compatibility boundaries.

`None` is allowed only when absence itself is a valid domain value, not as a discriminator for unrelated variants.

Examples:

- redirect vs dispatch are separate result types,
- app namespace vs plugin namespace are separate types,
- default dispatch vs explicit action dispatch are separate types,
- controller vs single action vs multi-action targets are separate types.

Arbitrary legacy `dict[str, Any]` shapes may exist only at parsing/normalization boundaries. Downstream matchers/resolvers/use cases consume closed typed variants.

### ADR-015 — Webasyst 4.2.0 source wins over conflicting current documentation
Status: accepted
Date: 2026-09-14

Official Webasyst developer documentation is a compatibility reference and SHOULD be consulted for migrated framework behavior.

When current documentation conflicts with the supplied Webasyst 4.2.0 source, the 4.2.0 source is authoritative unless a later ADR intentionally adopts newer behavior.

Known example: current naming-rules documentation describes `Controller -> Actions -> Action`, while 4.2.0 `waFrontController::getController()` and routing documentation use `Controller -> Single Action -> Multi Actions`. The migration preserves the 4.2.0 runtime behavior.

### ADR-016 — Routing and dispatch are typed staged compatibility pipelines
Status: accepted
Date: 2026-09-14

Frontend routing is modeled as two distinct stages:

```text
FrontendRouteRequest
    -> SystemRouteResolver
    -> SettlementResolution
    -> AppRouteResolver
    -> DispatchRequest
```

Backend routing uses a separate `BackendRouteRequest`/resolver and produces the same normalized `DispatchRequest` family.

A system settlement must not masquerade as a partially populated dispatch request. Defaults and legacy precedence rules are applied before constructing final dispatch variants.

Dispatch handler resolution preserves Webasyst 4.2.0 order:

```text
Controller
-> Single Action
-> Multi Actions
-> optional default-module fallback when try_default is enabled
-> 404
```

PHP `class_exists()` discovery is replaced by an explicit injectable handler registry. Per-application front-controller overrides are represented by an injectable dispatch-strategy registry.

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

Concrete native request path:

```text
HTTP request
    -> FastAPI route
    -> Pydantic input contract
    -> Application use case
    -> Repository / UnitOfWork Protocol
    -> Selected persistence adapter
    -> Database
```

Legacy compatibility request path:

```text
HTTP request
    -> presentation adapter
    -> legacy parser / normalizer
    -> Pydantic variant contracts
    -> routing / dispatch compatibility resolver
    -> registered handler / application boundary
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
    routing.py
    dispatch.py
    auth.py
    permissions.py
    api.py
    plugins.py
  application/
    contacts.py
    errors.py
    ports/
      contacts.py
      unit_of_work.py
      dispatch_registry.py
      auth.py
      cache.py
      filesystem.py
      events.py
      plugins.py
  infrastructure/
    persistence/sqlalchemy/
  compatibility/webasyst/
    routing/
    dispatch/
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
| `waRouting` | Webasyst compatibility parser + typed system/app/backend route resolvers |
| `waModel`, `waDb*` | repository/UoW ports + persistence adapters |
| `waFrontController` | typed dispatch resolver + strategy registry |
| `waController`, `waAction`, `*Actions` | explicit registered handler target variants |
| `waAPIController`, `waAPIMethod` | typed API routers + auth dependency + compatibility serializer |
| `waAuth`, OAuth adapters | auth use cases + auth/session/token ports + provider adapters |
| `waEvent` | typed event bus + legacy event bridge |
| `waPlugin`, `waPlugins` | plugin manifest/registry + typed hooks + compatibility bridge |

Do not recreate generic legacy escape hatches such as `waModel::query()` or global `waRequest::param()` as application-level APIs.

---

## Routing/dispatch compatibility rules

- Legacy route arrays/shorthand strings are parsed once at the boundary.
- Downstream code never receives arbitrary route dictionaries.
- Frontend and backend requests are different contracts.
- System settlement and final app dispatch are different contracts.
- Route patterns support literals, wildcards, `<name>`, and `<name:regex>` captures.
- Domain-specific routes and `default` fallback are characterized separately.
- Route order is significant.
- Routing-derived dispatch parameters override query-derived parameters according to 4.2.0 behavior.
- Backend module defaults to `backend`; frontend normalization applies `frontend` before final dispatch.
- Plugin namespace is a distinct variant, never `plugin: str | None`.
- Redirect is a routing outcome variant, never `redirect: str | None`.
- Invalid dispatch identifiers map to typed 400 errors.
- Missing routes/handlers map to typed 404 errors.
- Authorization, widgets, static-content routes, `priority_settlement`, generated page routes, and special callback paths are separate slices unless explicitly added by a later ADR.

---

## Persistence rules

- Repositories expose intent-oriented methods.
- No arbitrary query-builder access outside infrastructure.
- No DB-specific assumptions in application code.
- Database-specific SQL remains inside adapters.
- Use explicit transaction scopes.
- Every use case must be testable with fake repositories/UoW.
- Concrete persistence adapters require integration tests.
- Multiple adapters must pass the same persistence contract suite.
- Existing legacy tables are mapped; Python migrations do not recreate them blindly.

Initial production example:

```text
GOMAZON_DATABASE_URL=mysql+asyncmy://user:pass@host/webasyst
```

Test example:

```text
GOMAZON_DATABASE_URL=sqlite+aiosqlite:///:memory:
```

---

## Contact foundation scope

The first native Python contact endpoints are architectural proof endpoints, not legacy Webasyst API compatibility endpoints.

The first public profile contract excludes login/password/user/staff flags, sessions/tokens, email/phone/custom fields, photo/file handling, and other legacy semantics until dedicated slices migrate them.

---

## Web/API compatibility policy

For every migrated compatibility surface, characterize/test as applicable:

- method,
- route/domain matching,
- parsing and precedence,
- authentication/authorization,
- status,
- output shape,
- redirects,
- cookie/session mutation,
- error semantics.

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

Application and compatibility-core errors are framework-agnostic typed errors/results.

Presentation adapters translate them to HTTP responses. Webasyst compatibility adapters may translate them to legacy envelopes.

Raw SQLAlchemy/driver exceptions must not leak across the persistence boundary.

Redirects are typed successful routing outcomes, not exceptions.

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
Use characterization/golden tests for behavior claimed to match Webasyst. Routing tests must cite/source subtle 4.2.0 behavior when documentation differs.

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
7. Do not encode mutually exclusive states with collections of optional fields; use discriminated unions.
8. Normalize arbitrary legacy input once at a compatibility boundary and keep it out of downstream code.
9. Add/adjust application-owned Protocols before coupling services to infrastructure.
10. Add tests before or with behavior-changing implementation.
11. Prefer small vertical migration slices.
12. Do not mechanically translate PHP structure.
13. Preserve legacy behavior only when it is a compatibility requirement.
14. When current docs and 4.2.0 source disagree, follow ADR-015.
15. Update this file in the same change whenever architecture changes.
16. Add or supersede a numbered ADR; do not silently rewrite architectural history.
17. Do not claim Webasyst compatibility without characterization/compatibility tests.
18. Native Python endpoints and compatibility endpoints remain distinguishable until parity is proven.

---

## Foundation completion criteria

The foundation remains valid when:

- application use cases run without FastAPI/SQLAlchemy imports,
- persistence can be replaced through DI,
- Pydantic contracts cross architectural boundaries,
- ORM models remain infrastructure-private,
- legacy dictionaries are contained at compatibility parser boundaries,
- normalized variants avoid nullable state machines,
- routing/dispatch behavior is characterized against Webasyst 4.2.0,
- every introduced architectural decision is reflected in this file.
