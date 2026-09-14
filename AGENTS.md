# AGENTS.md

## Purpose

This repository is the Python rewrite target for Webasyst Framework 4.2.0 and the product built on top of it.

The migration goal is behavioral compatibility where it matters while replacing PHP framework internals with a typed, testable Python architecture.

This file is the canonical architecture record. Agents MUST update it in the same change whenever they introduce or change an architectural boundary, dependency direction, public contract, persistence abstraction, compatibility rule, migration strategy, or cross-cutting subsystem.

Do not leave important architecture decisions only in chat, PR descriptions, issues, code comments, design docs, or implementation plans.

Authoritative companion artifacts:

- Rewrite design: `docs/superpowers/specs/2026-09-14-webasyst-python-rewrite-design.md`
- Contacts plan: `docs/superpowers/plans/2026-09-14-contacts-foundation.md`
- Routing/dispatch design: `docs/superpowers/specs/2026-09-14-routing-dispatch-design.md`
- Routing/dispatch plan: `docs/superpowers/plans/2026-09-14-routing-dispatch.md`
- Official legacy documentation reference: `https://developers.webasyst.com/docs`

---

## Legacy source inventory

The supplied Webasyst 4.2.0 archive contains 7,569 files, including 2,468 PHP files.

Important legacy framework surfaces:

- `waSystem` — runtime/service locator, factories, dispatch, configuration, user state, plugins/events.
- `waRouting` — domain/path routing and URL generation.
- `waModel` and `waDb*` — CRUD/query execution, metadata, transactions and database adapters.
- `waFrontController`, `waController`, `waAction`, `waActions` — HTTP dispatch/controller execution.
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

Rules:

- no persistence operations in Pydantic models;
- no SQLAlchemy dependency in contracts;
- no hidden I/O in validators;
- explicit aliases for legacy field names when needed;
- public API contract changes require compatibility tests;
- ORM instances MUST NOT cross the persistence boundary.

### ADR-004 — DI uses explicit interfaces, not globals
Status: accepted
Date: 2026-09-14

Prefer constructor injection. Application-owned infrastructure boundaries use `typing.Protocol` where practical.

FastAPI `Depends` is permitted only in presentation/composition wiring. Application services must remain directly constructible in tests.

Forbidden: global mutable service locators, global DB sessions, hidden singleton dependencies, or recreating `waSystem::getInstance()` as a Python global container.

### ADR-005 — Repository + Unit of Work persistence boundary
Status: accepted
Date: 2026-09-14

Application code owns repository and Unit of Work protocols. Never pass SQLAlchemy `Session`/`AsyncSession` into application use cases. Repositories expose intent-oriented methods rather than query builders.

### ADR-006 — SQLAlchemy is infrastructure-private
Status: accepted
Date: 2026-09-14

ORM classes, sessions, engines, SQLAlchemy statements/results, driver types, and dialect-specific SQL stay inside the SQLAlchemy persistence adapter, except composition-root ownership of concrete resources.

### ADR-007 — Legacy compatibility lives in adapters
Status: accepted
Date: 2026-09-14

Webasyst-specific behavior is translated at explicit compatibility boundaries rather than spread through application code.

New application code consumes typed contracts, not PHP associative-array semantics.

### ADR-008 — Preserve existing data before redesigning schema
Status: accepted
Date: 2026-09-14

Initial migration reads/writes the existing Webasyst data safely where feasible. Do not perform destructive schema redesign during behavioral migration.

Alembic owns only schema changes introduced by the Python system; it must not blindly recreate the legacy schema.

### ADR-009 — Migration is incremental
Status: accepted
Date: 2026-09-14

Migrate in vertical, independently testable slices:

1. characterization fixtures;
2. packaging/composition root;
3. persistence ports + first adapter;
4. contacts;
5. routing/dispatch compatibility;
6. users/auth/sessions/permissions/tokens;
7. API compatibility;
8. events/hooks/plugins;
9. CLI/background/installer concerns as needed;
10. bundled applications by product priority;
11. rendering/template replacement independently from core migration.

### ADR-010 — First architectural proof is the contact vertical slice
Status: accepted
Date: 2026-09-14

Contacts/users prove settings, composition root, Pydantic contracts, repository/UoW protocols, SQLAlchemy adapter, use cases, HTTP endpoints, and testing seams.

Native contact endpoints are architecture-proof endpoints, not a claim of Webasyst API parity.

### ADR-011 — `waSystem` will not be recreated as a universal runtime object
Status: accepted
Date: 2026-09-14

Responsibilities concentrated in `waSystem` are split between composition root, settings, request context, routing adapters, application services, infrastructure ports/adapters, and plugin/event registries.

### ADR-012 — First contact slice maps only `wa_contact`
Status: accepted
Date: 2026-09-14

The first contact slice maps the base legacy `wa_contact` table only. Email/custom-field tables and authentication/session/token behavior are separate slices.

### ADR-013 — Initial relational persistence path is async
Status: accepted
Date: 2026-09-14

The first SQLAlchemy implementation uses `AsyncEngine`, `AsyncSession`, async repositories, and an async Unit of Work. MySQL/MariaDB uses `asyncmy`; tests may use `aiosqlite` without changing application code.

### ADR-014 — Mutually exclusive states use discriminated unions, not nullable bags
Status: accepted
Date: 2026-09-14

Nullable/optional fields MUST NOT encode mutually exclusive architectural states.

Use Pydantic discriminated unions and normalize legacy input at compatibility boundaries. `None` is allowed only when absence itself is a valid domain value.

Arbitrary legacy `dict[str, Any]` shapes may exist only at parsing/normalization boundaries. Downstream matchers/resolvers/use cases consume closed typed variants.

### ADR-015 — Webasyst 4.2.0 source wins over conflicting current documentation
Status: accepted
Date: 2026-09-14

Official Webasyst docs are a compatibility reference and SHOULD be consulted. When current docs conflict with the supplied 4.2.0 source, 4.2.0 source behavior is authoritative unless a later ADR intentionally adopts newer behavior.

Known example: current naming-rules docs describe `Controller -> Actions -> Action`, while 4.2.0 `waFrontController::getController()` resolves `Controller -> Single Action -> Multi Actions`.

### ADR-016 — Routing and dispatch are typed staged compatibility pipelines
Status: accepted
Date: 2026-09-14

Frontend routing:

```text
FrontendRouteRequest
  -> SystemRouteResolver
  -> SettlementResolution
  -> AppRouteResolver
  -> ResolvedDispatch
```

Backend routing uses a separate `BackendRouteRequest`/resolver and also produces `ResolvedDispatch`.

Handler resolution preserves 4.2.0 order:

```text
Controller
-> Single Action
-> Multi Actions
-> optional default retry only when explicitly requested
-> 404
```

PHP `class_exists()` discovery is replaced by an explicit injectable registry. Per-app front-controller overrides use an injectable strategy registry.

### ADR-017 — Routing seed variants preserve control-field presence semantics
Status: accepted
Date: 2026-09-14

Whether `module`, `action`, or `plugin` was explicitly present in a legacy route affects later Webasyst behavior and must not be collapsed into early defaults.

`DispatchSeed` therefore uses eight closed variants:

```text
EmptySeed
ModuleSeed
ActionOnlySeed
ActionSeed
PluginSeed
PluginActionOnlySeed
PluginModuleSeed
PluginActionSeed
```

System settlements also carry `AppRouteConstraint = AnyAppRouteConstraint | ModuleRouteConstraint` so only an explicitly supplied system `module` restricts candidate app routes. A module obtained from URL capture does not create this constraint.

### ADR-018 — Route data is separate from dispatch control and app-route miss is not routing 404
Status: accepted
Date: 2026-09-14

Arbitrary route/application params are represented as JSON-compatible `RouteData`, separate from module/action/plugin control state.

Final normalized routing output is:

```text
ResolvedDispatch
  request: DefaultDispatch | ActionDispatch
  route_data: RouteData
```

`AppSettlement` explicitly carries both `matched_prefix` and `remaining_path`; later stages do not reparse the original URL.

When no internal app route matches, Webasyst 4.2.0 continues to front-controller defaults rather than raising routing 404. Python must dispatch from the settlement seed plus frontend default module `frontend`. Handler lookup may still produce 404 later.

Final compatibility orchestration uses `LegacyDispatchOutcome = RedirectSettlement | HandlerDispatchOutcome`, not tuples/nullable fields.

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

Native request path:

```text
HTTP -> FastAPI -> Pydantic contract -> application use case -> port -> adapter -> DB
```

Legacy request path:

```text
HTTP
 -> presentation adapter
 -> legacy parser/normalizer
 -> Pydantic variant contracts
 -> routing/dispatch compatibility resolver
 -> registered handler/application boundary
```

---

## Target package layout

```text
src/gomazon_webasyst/
  composition/
  contracts/
    contacts.py
    routing.py
    dispatch.py
  application/
    contacts.py
    ports/
      unit_of_work.py
      contacts.py
      dispatch_registry.py
  infrastructure/
    persistence/sqlalchemy/
  compatibility/webasyst/
    routing/
    dispatch/
    service.py
  presentation/http/
    contacts.py
    legacy_dispatch.py
```

Compatibility may depend on contracts/application-owned ports. Application code must not import compatibility modules.

---

## Routing/dispatch compatibility rules

- system and app shorthand are normalized differently, matching `waRouting::formatRoutes()`;
- rule iteration order is significant;
- aliases/default domains are preserved;
- `temporarily_off` rules are skipped;
- disabled redirects are skipped;
- wildcard/named-regex captures follow 4.2.0 matching behavior;
- explicit route data overrides captured data;
- wildcard redirect interpolation preserves query string;
- valid UTF-8 percent-decoding happens before matching;
- trailing-slash canonicalization follows the 4.2.0 retry behavior used by this slice;
- explicit parent module constrains app routes by exact module;
- app captures fill only missing accumulated params, then explicit app rule data overrides;
- app-route miss falls through to frontend defaults;
- backend query/route precedence characterizes `waFrontController::getDispatchParams()`;
- non-empty dispatch identifiers must match `^[a-z_][a-z0-9_]*$` case-insensitively;
- `waActions::run(null)` maps to concrete `defaultAction` / `action_method="default"`;
- production `main.py` must not mount the legacy catch-all until route compatibility is deliberately activated.

---

## Persistence rules

- no arbitrary query-builder access outside infrastructure;
- no MySQL-specific assumptions in application code;
- explicit transaction scopes;
- use cases must run with fakes through DI;
- concrete adapters require integration tests;
- multiple adapters must pass the same persistence contract suite;
- existing legacy tables are mapped rather than blindly recreated.

Initial database URLs:

```text
GOMAZON_DATABASE_URL=mysql+asyncmy://user:pass@host/webasyst
GOMAZON_DATABASE_URL=sqlite+aiosqlite:///:memory:   # tests
```

---

## Error model

Application/compatibility errors are framework-agnostic typed errors. Presentation translates them to HTTP.

Routing/dispatch initial errors:

- `InvalidLegacyRoute`;
- `InvalidDispatchParameter` -> 400;
- `RouteNotFound` -> 404;
- `DispatchTargetNotFound` -> 404;
- `PluginUnavailable` -> 404.

Redirects are successful typed outcomes.

---

## Testing strategy

### Unit
Use fake repositories/UoW/registries. Core use cases and compatibility resolvers require no ASGI server or external DB.

### Architecture
Automated import-boundary tests prevent FastAPI/SQLAlchemy/drivers from leaking into contracts/application.

### Persistence contract
Reusable behavioral tests run against each concrete persistence adapter.

### Compatibility characterization
Tests reference the relevant Webasyst 4.2.0 method/class when behavior is subtle or docs conflict with source.

### Integration
Cover DB wiring and ASGI compatibility flow. CI installs dev drivers and runs the full suite on Python 3.12.

---

## Explicit routing non-goals for the current slice

Do not silently add auth/session/permission checks, CSRF, widgets, `priority_settlement`, generated page routes, static-content serving, PHP autoloading, plugin lifecycle/locale initialization, or `waRouting::getUrl` parity. Each requires its own compatibility slice/ADR.

---

## Agent implementation rules

1. Read this file before changing architecture or adding a subsystem.
2. Read the relevant accepted design and implementation plan.
3. Preserve dependency direction.
4. Do not bypass DI with globals.
5. Do not leak ORM/session/engine/driver types into contracts/use cases.
6. Use Pydantic v2 at explicit boundaries.
7. Use discriminated unions for variant state; do not add nullable control bags for convenience.
8. Parse legacy dictionaries once at compatibility boundaries.
9. Add/adjust application-owned Protocols before coupling to infrastructure.
10. Use tests before/with behavior changes and source-backed characterization for legacy semantics.
11. Prefer small vertical slices.
12. Do not mechanically translate PHP structure.
13. Update this file in the same change whenever architecture changes.
14. Add/supersede numbered ADRs; do not silently rewrite architectural history.
15. Do not claim Webasyst compatibility without characterization tests.
16. Keep native Python endpoints distinguishable from compatibility endpoints until parity is proven.

---

## Current foundation completion state

The foundation is considered proven when CI confirms:

- application use cases run without FastAPI/SQLAlchemy imports;
- persistence is replaceable through DI;
- MySQL/MariaDB selection is composition-root configuration;
- Pydantic contracts cross architectural boundaries;
- ORM models stay infrastructure-private;
- contact slice passes unit/architecture/persistence/integration/HTTP tests;
- routing/dispatch slice passes contract/pattern/parser/resolver/registry/strategy/ASGI tests;
- every new architectural decision is reflected here.
