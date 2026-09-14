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
- Auth/session design: `docs/superpowers/specs/2026-09-14-auth-session-design.md`
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

### ADR-019 — Serialized discriminator values are declared through EnumStr
Status: accepted
Date: 2026-09-14

String-valued contract discriminators MUST derive from the shared `EnumStr` base (`enum.StrEnum`) rather than repeat raw magic strings across models.

Pydantic v2 field discriminators still require each concrete model discriminator field to be typed as `Literal[...]`; therefore the required pattern is `kind: Literal[NamespaceKind.APP] = NamespaceKind.APP`, not `kind: NamespaceKind = NamespaceKind.APP`.

Each semantic discriminator domain has its own enum. Raw legacy/JSON strings remain accepted at validation boundaries, and JSON serialization emits the original string values.

### ADR-020 — Expected negative outcomes use explicit typed results, not sentinel absence
Status: accepted
Date: 2026-09-14

Expected absence, rejection, invalidation, or other ordinary negative outcomes MUST be represented by explicit typed result variants rather than `None`, `False`, empty collections, magic strings, or overloaded exceptions.

Examples include identity lookup miss, rejected credentials, expired/revoked sessions, unsupported credential schemes, importer selection failure, provider selection failure, and target/plugin resolution failures when those outcomes are part of normal control flow.

Use discriminated Pydantic result unions with `EnumStr` error/status domains. `None` remains valid only when absence itself is the domain value, not when it stands for an operation failure or branch of control flow.

Infrastructure faults such as database unavailability, I/O failure, timeout, corruption, or programming errors are not normal negative outcomes and MUST NOT be collapsed into a `NOT_FOUND`/`REJECTED` result. They propagate as typed infrastructure/application errors according to the boundary.

Security-sensitive public adapters may intentionally coarsen internal result types, for example mapping identity-not-found and password-mismatch to one external `INVALID_CREDENTIALS` response to avoid information disclosure.

### ADR-021 — Extensible lookup and selection use policies/registries, not method proliferation
Status: accepted
Date: 2026-09-14

When a behavior is expected to gain new lookup schemes, providers, importers, targets, identity sources, OAuth providers, storage backends, or similar strategies, application-owned ports MUST NOT grow one method per current variant (`find_by_login`, `find_by_email`, `find_by_phone`, etc.).

Represent the requested scheme as data and route it through policy/registry boundaries:

```text
input
  -> ordered policy set
  -> typed lookup/selection plan
  -> registry/directory keyed by scheme/provider id
  -> explicit typed result
```

Extension identifiers such as identity-key schemes are open extension points and SHOULD remain strings/value objects rather than closed enums when third-party or later-added schemes must be registerable without modifying core contracts.

Closed result/status/discriminator domains still use `EnumStr` per ADR-019.

Adding a new scheme/provider SHOULD require registering a new policy/resolver/adapter, not editing existing use-case branches or adding a new method to a central repository/service interface.

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
    auth.py
  application/
    contacts.py
    auth.py
    ports/
      unit_of_work.py
      contacts.py
      dispatch_registry.py
      identity_directory.py
      auth_subjects.py
      password_verifier.py
      session_state.py
      auth_session_registry.py
  infrastructure/
    persistence/sqlalchemy/
    auth/
    sessions/
  compatibility/webasyst/
    routing/
    dispatch/
    auth/
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

## Auth/session compatibility rules

The first auth slice is backend password authentication plus session create/resolve/revoke.

- identity lookup is driven by an ordered `LoginPolicySet` and an `IdentityDirectory`, not `find_by_*` methods;
- `IdentityKey.scheme` is an open extension identifier and is not a closed enum;
- expected lookup, credential and session failures are explicit typed result variants;
- public login responses may coarsen internal rejection reasons to avoid account enumeration;
- legacy default password verification is MD5-compatible but hashing remains behind an injected `PasswordVerifier`;
- application code must not contain MD5/password-hash implementation details;
- successful password login MUST NOT automatically rehash or write a new password in this slice;
- session state analogous to legacy `auth_user` and active-auth registry state in `wa_contact_auths` are separate ports;
- `wa_contact_auths` is a registry/revocation table, not the session-state store;
- credential-version invalidation is represented through an injected token factory and explicit `CREDENTIALS_CHANGED` session result;
- remember-me, one-time password, frontend confirmation/signup, permissions, OAuth/social/Webasyst ID, API OAuth2 tokens and PHP-session-file interoperability are separate slices.

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

Ordinary negative outcomes that callers are expected to branch on are typed result variants per ADR-020. Infrastructure/programming failures remain exceptional and must not be disguised as ordinary negative outcomes.

Routing/dispatch initial errors include `InvalidLegacyRoute`, `InvalidDispatchParameter`, `RouteNotFound`, `DispatchTargetNotFound`, and `PluginUnavailable`.

Redirects are successful typed outcomes.

---

## Testing strategy

### Unit
Use fake repositories/UoW/registries/policies. Core use cases and compatibility resolvers require no ASGI server or external DB.

### Architecture
Automated import-boundary tests prevent FastAPI/SQLAlchemy/drivers/concrete crypto or password algorithms from leaking into contracts/application.

### Persistence contract
Reusable behavioral tests run against each concrete persistence adapter.

### Compatibility characterization
Tests reference the relevant Webasyst 4.2.0 method/class when behavior is subtle or docs conflict with source.

### Integration
Cover DB wiring, ASGI compatibility flow, and auth/session composition. CI installs dev drivers and runs the full suite on Python 3.12.

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
8. Declare serialized string discriminator values through `EnumStr` enums; never duplicate raw discriminator magic strings across contract models.
9. Represent expected negative outcomes as explicit typed result variants; do not use `None`, `False`, empty values, or exceptions as ordinary branch markers.
10. For extensible lookup/selection, use policies plus registries/directories keyed by scheme/provider id; do not grow central interfaces with `find_by_*` or one-method-per-provider APIs.
11. Parse legacy dictionaries once at compatibility boundaries.
12. Add/adjust application-owned Protocols before coupling to infrastructure.
13. Use tests before/with behavior changes and source-backed characterization for legacy semantics.
14. Prefer small vertical slices.
15. Do not mechanically translate PHP structure.
16. Update this file in the same change whenever architecture changes.
17. Add/supersede numbered ADRs; do not silently rewrite architectural history.
18. Do not claim Webasyst compatibility without characterization tests.
19. Keep native Python endpoints distinguishable from compatibility endpoints until parity is proven.

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
- auth/session slice, when implemented, passes contract/policy/directory/password/session/persistence/integration tests;
- every new architectural decision is reflected here.
