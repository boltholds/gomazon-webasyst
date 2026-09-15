# AGENTS.md

## Purpose

This repository is the Python rewrite target for Webasyst Framework 4.2.0 and the product built on top of it.

The migration goal is behavioral compatibility where it matters while replacing PHP framework internals with a typed, testable Python architecture.

This file is the canonical architecture record. Agents MUST update it in the same change whenever they introduce or change an architectural boundary, dependency direction, public contract, persistence abstraction, compatibility rule, migration strategy, or cross-cutting subsystem.

Authoritative companion artifacts:

- Rewrite design: `docs/superpowers/specs/2026-09-14-webasyst-python-rewrite-design.md`
- Contacts plan: `docs/superpowers/plans/2026-09-14-contacts-foundation.md`
- Routing/dispatch design: `docs/superpowers/specs/2026-09-14-routing-dispatch-design.md`
- Routing/dispatch plan: `docs/superpowers/plans/2026-09-14-routing-dispatch.md`
- Auth/session design: `docs/superpowers/specs/2026-09-14-auth-session-design.md`
- Persistent-login design: `docs/superpowers/specs/2026-09-14-persistent-login-design.md`
- Access-control design: `docs/superpowers/specs/2026-09-15-access-control-design.md`
- State backend + API OAuth2 design: `docs/superpowers/specs/2026-09-15-state-backends-api-oauth2-design.md`
- Official legacy documentation reference: `https://developers.webasyst.com/docs`

---

## Legacy source inventory

Important legacy framework surfaces:

- `waSystem` — runtime/service locator, factories, dispatch, configuration, user state, plugins/events.
- `waRouting` — domain/path routing and URL generation.
- `waModel` / `waDb*` — CRUD/query execution, metadata, transactions and database adapters.
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

Use Python 3.12+, FastAPI/Starlette, Pydantic v2, `pydantic-settings`, SQLAlchemy 2.x as the first relational persistence adapter, Alembic for Python-owned schema migrations, and pytest. FastAPI is a presentation adapter and must not leak into application/domain contracts.

### ADR-002 — Database replaceability is a hard requirement
Status: accepted
Date: 2026-09-14

Business logic MUST NOT depend on a concrete database, SQLAlchemy session/model, SQL dialect, or driver. Concrete persistence is selected at the composition root. MySQL/MariaDB with the existing Webasyst schema is the first target; replacing the backend must not require rewriting use cases.

### ADR-003 — Pydantic v2 contracts define boundaries
Status: accepted
Date: 2026-09-14

Pydantic v2 models are canonical serialized/cross-boundary contracts. No persistence I/O, SQLAlchemy dependency, hidden I/O, or ORM instances may cross those boundaries.

### ADR-004 — DI uses explicit interfaces, not globals
Status: accepted
Date: 2026-09-14

Prefer constructor injection and application-owned `Protocol`s. FastAPI `Depends` is limited to presentation/composition wiring. No global service locator, global DB session, hidden singleton, or Python recreation of `waSystem::getInstance()`.

### ADR-005 — Repository + Unit of Work persistence boundary
Status: accepted
Date: 2026-09-14

Application code owns repository/UoW protocols. Repositories expose intent-oriented methods, not generic query builders. SQLAlchemy sessions never enter use cases.

### ADR-006 — SQLAlchemy is infrastructure-private
Status: accepted
Date: 2026-09-14

ORM classes, sessions, engines, statements/results, driver types, and dialect-specific SQL stay inside the SQLAlchemy adapter except composition-root ownership of concrete resources.

### ADR-007 — Legacy compatibility lives in adapters
Status: accepted
Date: 2026-09-14

Webasyst-specific behavior is translated at explicit compatibility boundaries. New application code consumes typed contracts, not PHP associative-array semantics.

### ADR-008 — Preserve existing data before redesigning schema
Status: accepted
Date: 2026-09-14

Initial migration reads/writes existing Webasyst data safely. Do not destructively redesign the legacy schema during behavioral migration. Alembic owns only Python-introduced schema changes.

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

Contacts/users prove settings, DI, Pydantic contracts, repository/UoW seams, SQLAlchemy adapter, HTTP endpoints, and testing boundaries. Native contact endpoints are architecture-proof endpoints, not Webasyst API parity.

### ADR-011 — `waSystem` will not be recreated as a universal runtime object
Status: accepted
Date: 2026-09-14

Responsibilities concentrated in `waSystem` are split between composition root, settings, request context, routing adapters, application services, infrastructure ports/adapters, and plugin/event registries.

### ADR-012 — First contact slice maps only `wa_contact`
Status: accepted
Date: 2026-09-14

The first contact slice maps only the base `wa_contact` table. Emails, custom fields, auth/session/token behavior are separate slices.

### ADR-013 — Initial relational persistence path is async
Status: accepted
Date: 2026-09-14

The first SQLAlchemy implementation uses `AsyncEngine`, `AsyncSession`, async repositories, and async UoW. MySQL/MariaDB uses `asyncmy`; tests may use `aiosqlite` without changing application code.

### ADR-014 — Mutually exclusive states use discriminated unions, not nullable bags
Status: accepted
Date: 2026-09-14

Nullable/optional fields MUST NOT encode mutually exclusive architectural states. Use discriminated unions and normalize legacy input at compatibility boundaries. `None` is valid only when absence itself is a domain value.

### ADR-015 — Webasyst 4.2.0 source wins over conflicting current documentation
Status: accepted
Date: 2026-09-14

Official docs are a compatibility reference. When current docs conflict with supplied 4.2.0 source behavior, 4.2.0 source is authoritative unless a later ADR intentionally adopts newer behavior.

### ADR-016 — Routing and dispatch are typed staged compatibility pipelines
Status: accepted
Date: 2026-09-14

Frontend routing is `FrontendRouteRequest -> SystemRouteResolver -> SettlementResolution -> AppRouteResolver -> ResolvedDispatch`. Backend uses a separate request/resolver but produces the same normalized dispatch family. Handler resolution preserves 4.2.0 order: Controller -> Single Action -> Multi Actions -> optional explicit default retry -> 404. PHP `class_exists()` discovery is replaced by explicit registries/strategies.

### ADR-017 — Routing seed variants preserve control-field presence semantics
Status: accepted
Date: 2026-09-14

Presence/absence of legacy `module`, `action`, and `plugin` is semantically significant. `DispatchSeed` therefore uses explicit closed variants rather than nullable fields. Explicit parent module constraints are modeled separately from values obtained through captures.

### ADR-018 — Route data is separate from dispatch control and app-route miss is not routing 404
Status: accepted
Date: 2026-09-14

Arbitrary route/application params are JSON-compatible `RouteData`, separate from module/action/plugin control state. `ResolvedDispatch` contains normalized dispatch request plus route data. App-route miss falls through to frontend defaults; handler lookup may later produce 404.

### ADR-019 — Serialized discriminator values are declared through EnumStr
Status: accepted
Date: 2026-09-14

String-valued discriminator domains derive from shared `EnumStr` (`StrEnum`) instead of repeating magic strings. Pydantic v2 discriminator fields still use `Literal[EnumMember] = EnumMember`. Raw legacy/JSON strings remain accepted and serialize back to their string values.

### ADR-020 — Expected negative outcomes use explicit typed results, not sentinel absence
Status: accepted
Date: 2026-09-14

Expected absence, rejection, invalidation, expiration, or other normal negative outcomes MUST use explicit typed result variants rather than `None`, `False`, empty values, magic strings, or overloaded exceptions. Infrastructure faults such as DB unavailability, I/O failure, timeout, or corruption remain exceptional and must not be collapsed into ordinary negative results. Public security adapters may intentionally coarsen internal reasons to prevent information disclosure.

### ADR-021 — Extensible lookup and selection use policies/registries, not method proliferation
Status: accepted
Date: 2026-09-14

When behavior is expected to gain new schemes/providers/importers/targets/backends, application-owned ports MUST NOT grow one method per current variant (`find_by_login`, `find_by_email`, `find_by_phone`, etc.). Use ordered policies to produce a typed lookup/selection plan, then a registry/directory keyed by an open scheme/provider identifier. Adding a new scheme should require registration, not editing use-case branches or central interfaces. Closed result/status domains still use `EnumStr`.

### ADR-022 — Correlated identifiers use immutable value objects instead of primitive pairs
Status: accepted
Date: 2026-09-14

Identifiers that form one stable domain identity and repeatedly travel together across application ports MUST be represented by immutable value objects rather than parallel primitive arguments.

For auth/session state:

```python
from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class SessionId:
    value: str

@dataclass(slots=True, frozen=True)
class AuthSessionKey:
    contact_id: int
    session_id: SessionId
```

`AuthSessionRegistry` consumes `AuthSessionKey` instead of separate `contact_id`/`session_id` parameters. `SessionStateStore` accepts `SessionId` only for the first opaque lookup because the contact id is not known yet; after resolution, subsequent state-store and registry operations use `AuthSessionKey`.

Pydantic remains canonical for serialized/cross-boundary contracts. Small internal VOs MAY use `@dataclass(slots=True, frozen=True)` when they need value semantics but no wire-format validation/serialization.

### ADR-023 — Optional/None is reserved for genuine nullable data boundaries
Status: accepted
Date: 2026-09-14

`T | None` / `Optional[T]` MUST NOT be used as an operation result, lookup miss, registry miss, lifecycle state, dispatch/match state, or omitted-control marker. Those cases use explicit result variants, immutable state/value objects, or separate entry points.

Allowed uses are limited to genuine nullable data imposed by an external schema/protocol, such as nullable legacy ORM columns and the standard `__aexit__` exception arguments. Raw third-party/library APIs may yield `None` internally, but adapters MUST normalize that value immediately before it crosses an application/compatibility boundary.

The architecture test suite enforces this rule across source annotations.

### ADR-024 — Persistent authentication is a strategy bridge, not a fixed token format
Status: accepted
Date: 2026-09-14

Application code treats a long-lived login credential as an opaque `PersistentCredential`. Acceptance is performed by an ordered `PersistentCredentialStrategy` resolver chain, while issuance is a separately injected `PersistentCredentialIssuer`. The Webasyst 4.2.0 deterministic `auth_token` format is compatibility-only and is registered as the terminal fallback for unprefixed credentials. Future formats such as a prefixed opaque v2 token may be accepted before the legacy strategy and may become the configured issuer without changing persistent-login use cases.

### ADR-025 — Persistent-login intent and credential transport are separate from primary authentication
Status: accepted
Date: 2026-09-14

Do not add `remember: bool`, nullable remember fields, cookie types, or transport settings to `BackendPasswordCredentials`. Password authentication establishes a normal session only. Persistent issuance is an explicit `IssuePersistentCredential` operation invoked after successful authentication when the caller requests persistence. Restore results carry a typed `RefreshPersistentCredential | ClearPersistentCredential | KeepPersistentCredential` disposition; presentation maps that intent to cookies. The legacy `remember` cookie is only UI preference state and is not an authentication credential. If remember-me is globally disabled, persistent restore is not invoked and an existing `auth_token` is left untouched, matching 4.2.0.

### ADR-026 — Access control preserves the numeric legacy ACL model instead of flattening it into RBAC
Status: accepted
Date: 2026-09-15

Framework access control is a typed compatibility ACL over `wa_contact_rights`, `wa_group`, and `wa_user_groups`, not a new `Role -> Permission` schema. Right values remain integers because Webasyst semantics include personal assignments, group assignments, guests, numeric levels, `MAX(value)` aggregation, limited/full backend levels and application-defined numeric rights. Effective access is represented with typed variants such as `FiniteRight`, `UnlimitedRight`, `NoAppAccess`, `LimitedAppAccess`, `FullAppAccess`, and `GlobalAdminAccess`; bool `can_*` is not the canonical framework contract.

### ADR-027 — Signed legacy principal identifiers are persistence details only
Status: accepted
Date: 2026-09-15

Application contracts use explicit `UserTarget`, `GroupTarget`, and `GuestsTarget` variants. The legacy `wa_contact_rights.group_id` encoding (`user -> negative contact id`, `group -> positive group id`, `guests -> 0`) is translated only by the compatibility/infrastructure persistence adapter. Negative principal ids MUST NOT appear in application ports, use-case requests, or result contracts.

### ADR-028 — ACL mutations use a dedicated transactional UoW and pure legacy mutation plans
Status: accepted
Date: 2026-09-15

Multi-table ACL/group writes use an application-owned `AccessControlUnitOfWork` containing narrow group, membership, rights and subject ports. Webasyst-specific `backend` cleanup semantics are expressed by a pure `LegacyRightsMutationPolicy -> RightsMutationPlan`; repositories execute plans but do not duplicate business rules. Generic right assignment cannot mutate reserved `backend`; callers use explicit app/global access operations. Group deletion intentionally removes memberships, group-owned rights, and the group atomically, improving on 4.2.0's orphan-right behavior while preserving observable access semantics.

### ADR-029 — Access-control administration is authorized inside the mutation transaction
Status: accepted
Date: 2026-09-15

Every ACL/group/membership mutation receives the authenticated actor and checks an injected application-owned `AccessAdministrationPolicy` before writing. The first compatibility policy allows administration only to subjects with effective `GlobalAdminAccess`. Authorization is evaluated using the same `AccessControlUnitOfWork` transaction as the mutation so the decision and state change share one transactional view. Expected denial is a typed result; repositories are not security boundaries and presentation must not bypass use cases.

### ADR-030 — Runtime session state backend selection is a composition concern
Status: accepted
Date: 2026-09-15

`SessionStateStore` remains the domain-specific application-owned port for session create/resolve/revoke semantics. Concrete runtime storage is selected only in composition through an extensible `SessionStateProviderRegistry` keyed by open `StateProviderName` values and factories implementing `SessionStateStoreFactory`. One application container resolves exactly one store instance and shares it across password authentication, session resolution/logout, and persistent-login restoration; providers MUST NOT create a new store per request or use-case call. The default provider is in-process memory, but Redis, KeyDB/Dragonfly, Supabase/Postgres, or other adapters may be registered without changing application use cases or adding central backend conditionals. Future provider implementations must satisfy the same `SessionStateStore` behavioral contract. For Supabase, durable Postgres state is authoritative; Realtime may propagate revocation/invalidation or cache synchronization but is not itself the source of truth.

### ADR-031 — Webasyst API OAuth credentials preserve the existing legacy tables
Status: accepted
Date: 2026-09-15

The compatibility implementation maps `wa_api_auth_codes` and `wa_api_tokens` directly; these tables remain authoritative for the Webasyst 4.2.0 API credential slice. No replacement OAuth schema or migration is introduced. SQLAlchemy rows remain infrastructure-private and application code consumes typed credential records through `AuthorizationCodeRepository`, `ApiTokenRepository`, and `ApiCredentialUnitOfWork`.

### ADR-032 — Reusable authorization codes and subject/client token reuse are compatibility policies
Status: accepted
Date: 2026-09-15

Webasyst 4.2.0 authorization codes remain reusable until their 180-second expiry because the legacy token controller does not consume them after exchange. This is represented by injected `AuthorizationCodeExchangePolicy`; a stricter future mode may consume codes without changing repositories/use cases. Likewise, the legacy rule that one access token is reused for `(contact_id, client_id)` and only its scope is updated is isolated behind `ApiTokenIssuePolicy` and the shared `ApiTokenIssuer`, not hard-coded into transport or persistence interfaces.

### ADR-033 — Nullable legacy token columns normalize to explicit application state
Status: accepted
Date: 2026-09-15

`wa_api_tokens.last_use_datetime` and `wa_api_tokens.expires` are genuinely nullable ORM fields. SQL adapters immediately normalize them to `ApiTokenNeverUsed | ApiTokenLastUsedAt` and `ApiTokenNeverExpires | ApiTokenExpiresAt`. `None` must not escape the persistence boundary or become an application result/state sentinel.

### ADR-034 — API credential core is separate from API transport and authorization
Status: accepted
Date: 2026-09-15

The credential core owns authorization-code issue/exchange, implicit token issue, token resolution/touch and revoke. Bearer/query token extraction, OAuth redirect/consent endpoints, installed-app filtering, ACL/scope authorization, API method dispatch, JSON/XML legacy envelopes and HTTP error mapping are a later presentation/API-framework slice. No FastAPI/Starlette dependency belongs in API credential application code.

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

---

## Target package layout

```text
src/gomazon_webasyst/
  composition/
    access_control.py
  contracts/
    contacts.py
    routing.py
    dispatch.py
    auth.py
    persistent_login.py
    access_control.py
  application/
    contacts.py
    auth.py
    persistent_login.py
    persistent_values.py
    session_establishment.py
    access_control.py
    access_values.py
    rights_evaluator.py
    rights_mutation_policy.py
    ports/
      unit_of_work.py
      contacts.py
      dispatch_registry.py
      identity_directory.py
      auth_subjects.py
      password_verifier.py
      session_state.py
      session_validation.py
      auth_session_registry.py
      persistent_credentials.py
      access_control_uow.py
      groups.py
      memberships.py
      rights.py
      access_subjects.py
      access_admin_policy.py
  infrastructure/
    persistence/sqlalchemy/
    auth/
      persistent_credentials.py
    access_control/sqlalchemy/
    sessions/
  compatibility/webasyst/
    routing/
    dispatch/
    auth/
      persistent.py
    access_control/
      principals.py
      evaluation.py
      mutation.py
    service.py
  presentation/http/
    contacts.py
    legacy_dispatch.py
```

Compatibility may depend on contracts/application-owned ports. Application code must not import compatibility modules.

---

## Routing/dispatch compatibility rules

- system and app shorthand normalization match `waRouting::formatRoutes()` semantics;
- route order is significant;
- aliases/default domains are preserved;
- `temporarily_off`/disabled routes are skipped;
- wildcard/named-regex captures follow characterized 4.2.0 behavior;
- explicit route data overrides captured data;
- wildcard redirects preserve query string;
- valid UTF-8 percent-decoding happens before matching;
- app-route miss falls through to frontend defaults;
- backend query/route precedence characterizes `waFrontController::getDispatchParams()`;
- dispatch identifiers are validated;
- `waActions::run(null)` maps to concrete default action behavior;
- production `main.py` must not mount the legacy catch-all until parity is deliberately activated.

---

## Auth/session compatibility rules

The first auth slice is backend password authentication plus session create/resolve/revoke; persistent login is the next compatibility layer on top of it.

- identity lookup is driven by ordered `LoginPolicySet` + `IdentityDirectory`, not `find_by_*` methods;
- `IdentityKey.scheme` is an open extension identifier, not a closed enum;
- expected lookup, credential and session failures are explicit typed result variants;
- public login responses may coarsen internal rejection reasons to avoid account enumeration;
- legacy default password verification is MD5-compatible but hashing remains behind injected `PasswordVerifier`;
- application code must not contain concrete MD5/password-hash logic;
- successful password login MUST NOT automatically rehash/write a new password in this slice;
- session state analogous to legacy `auth_user` and `wa_contact_auths` registry state are separate ports;
- `wa_contact_auths` is a registry/revocation table, not the session-state store;
- `SessionId` is the opaque initial locator; established auth-session identity is `AuthSessionKey`;
- credential-version invalidation uses an injected token factory and explicit `CREDENTIALS_CHANGED` result;
- persistent credential acceptance uses an ordered strategy resolver; issuance is configured separately;
- legacy `auth_token` is stateless, deterministic, 30-day and compatibility-only; successful restore refreshes the same credential and invalid credentials are cleared by transport;
- ordinary `remember=false` does not itself mean revoke; persistence issuance and revocation/clear are separate operations;
- the legacy `remember` cookie is UI preference state and must not enter auth application contracts;
- OTP, frontend confirmation/signup, OAuth/social/Webasyst ID, opaque v2 persistence, and PHP-session-file interoperability are later slices.

---

## API credential compatibility rules

- `wa_api_auth_codes` and `wa_api_tokens` are mapped as existing legacy storage, not redesigned;
- compatibility-generated codes/tokens are 32 lowercase hexadecimal characters using secure Python entropy;
- authorization-code lifetime is exactly 180 seconds by default;
- code expiry follows the characterized legacy comparison: expired only when `expires < now`, so the exact boundary remains valid;
- successful Webasyst-compatible code exchange keeps the code reusable until expiry;
- one token is reused for `(contact_id, client_id)`; changed scope updates that token instead of rotating it;
- newly created compatibility tokens use the explicit never-expires state corresponding to SQL `NULL`;
- successful token resolution updates `last_use_datetime` transactionally;
- token/code collisions and expected concurrent state changes are typed outcomes;
- raw scope CSV encoding stays in the Webasyst compatibility adapter;
- HTTP token extraction, consent/redirect flows and API method authorization are not part of this credential slice.

---

## Access-control compatibility rules

- exact Webasyst 4.2.0 source is authoritative for rights/group behavior;
- effective user rights aggregate personal, group and guest assignments using `MAX(value)` per right name;
- `webasyst/backend > 0` yields effective global-admin access for non-Webasyst applications;
- application `backend == 1` means limited access and `backend >= 2` means full/app-admin access;
- full/global access yields typed unlimited named rights rather than a leaked `PHP_INT_MAX` sentinel;
- without app backend access, named rights resolve to finite zero;
- with limited access, exact named rights are evaluated first; an exact zero/falsy value for a dotted right may fall back to the corresponding `.all` right;
- non-zero negative named-right values are preserved and do not trigger `.all` fallback;
- `RightName` and `AppId` are open identifiers; closed access/result states use `EnumStr`;
- generic named-right assignment cannot mutate reserved `backend`; app/global backend state uses dedicated operations;
- setting global backend clears all target assignments first, matching `waContactRightsModel::save()`;
- setting application backend to anything other than limited (`1`) clears that target+app scope first;
- generic zero assignment is represented as explicit revoke/delete;
- new membership writes require an existing contact with `is_user > 0`; legacy read paths tolerate older inconsistent rows;
- `wa_group.cnt` is recomputed from memberships joined to contacts with `is_user > 0`;
- group deletion intentionally removes group-owned rights as an integrity improvement over 4.2.0;
- ACL mutation authorization is checked inside the same transaction as the write;
- application installation/catalog validation is deferred until the application registry slice; callers must use installed/configured app ids in this slice;
- no global/static rights cache is introduced in the first Python ACL slice.

---

## Persistence rules

- no arbitrary query-builder access outside infrastructure;
- no database-specific assumptions in application code;
- explicit transaction scopes;
- use cases must run with fakes through DI;
- concrete adapters require integration tests;
- existing legacy tables are mapped rather than blindly recreated;
- ACL/group writes spanning `wa_group`, `wa_user_groups`, `wa_contact_rights`, and ACL-relevant `wa_contact` reads use the dedicated access-control UoW;
- API credential writes spanning authorization-code exchange and token issue/reuse use the dedicated API credential UoW.

Initial examples:

```text
GOMAZON_DATABASE_URL=mysql+asyncmy://user:pass@host/webasyst
GOMAZON_DATABASE_URL=sqlite+aiosqlite:///:memory:   # tests
```

---

## Error model

Application/compatibility errors are framework-agnostic. Presentation translates them to HTTP. Ordinary negative outcomes are typed result variants per ADR-020; infrastructure/programming failures remain exceptional.

---

## Testing strategy

### Unit
Use fakes for repositories/UoW/registries/policies. Core use cases and compatibility resolvers require no ASGI server or external DB. ACL evaluator, fallback policy, mutation planner, administration policy and group/membership/right use cases are pure/fake-testable. API credential issue/exchange/resolve/revoke and token reuse policies are also fake-testable without HTTP or an external database.

### Architecture
Prevent FastAPI/SQLAlchemy/drivers/concrete crypto/password algorithms from leaking into contracts/application. Enforce ADR-023 by rejecting unexpected `Optional`/`T | None` annotations outside genuine nullable schema/protocol boundaries. Persistent-login application code must not import legacy token-format classes or cookie/HTTP types. ACL application code must not import SQLAlchemy or Webasyst compatibility implementations, expose signed principal IDs, use bool-sentinel results, or handle reserved `backend` mutation rules outside the compatibility policy layer. API credential application code must not import FastAPI, Starlette, SQLAlchemy, `secrets`, Webasyst compatibility implementations, or raw legacy OAuth table names.

### Persistence contract
Reusable behavioral tests run against concrete persistence adapters.

### Compatibility characterization
Reference relevant Webasyst 4.2.0 methods/classes when behavior is subtle or documentation conflicts with source. ACL characterization covers effective `MAX` aggregation, global/app backend overrides, `.all` fallback, principal encoding, mutation cleanup, zero-as-delete and group-count semantics. API credential characterization covers table shape, 180-second code lifetime, reusable code exchange and subject/client token reuse.

### Integration
Cover DB wiring, ASGI compatibility flow, auth/session composition, persistent-login issuance/restore, SQLite ACL/group vertical flows, and the SQLite API credential flow from code issue through exchange/reuse/resolve/revoke. CI runs the full suite on Python 3.12.

---

## Agent implementation rules

1. Read this file before changing architecture or adding a subsystem.
2. Read the relevant accepted design and implementation plan.
3. Preserve dependency direction.
4. Do not bypass DI with globals.
5. Do not leak ORM/session/engine/driver types into contracts/use cases.
6. Use Pydantic v2 at serialized/cross-boundary interfaces.
7. Use discriminated unions for variant state; do not add nullable control bags for convenience.
8. Declare serialized string discriminator values through `EnumStr` enums.
9. Represent expected negative outcomes as explicit typed results; do not use sentinel absence or bools for ordinary branches.
10. For extensible lookup/selection, use policies plus registries/directories keyed by open scheme/provider identifiers; do not grow `find_by_*` APIs.
11. Replace repeated correlated primitive pairs with immutable internal VOs; prefer `@dataclass(slots=True, frozen=True)` for non-wire value objects.
12. Reserve `T | None` / `Optional[T]` for genuine external data/protocol nullability only; never use it for operation/lookup results, lifecycle state, dispatch/match state, or omitted controls.
13. Keep primary authentication, persistence issuance, and credential transport as separate operations/boundaries; do not add remember flags to password credentials.
14. Parse legacy dictionaries once at compatibility boundaries.
15. Add/adjust application-owned Protocols before coupling to infrastructure.
16. Use tests before/with behavior changes and source-backed characterization for legacy semantics.
17. Prefer small vertical slices.
18. Do not mechanically translate PHP structure.
19. Update this file in the same change whenever architecture changes.
20. Add/supersede numbered ADRs; do not silently rewrite architectural history.
21. Do not claim Webasyst compatibility without characterization tests.
22. Keep native Python endpoints distinguishable from compatibility endpoints until parity is proven.
23. Keep signed Webasyst ACL principal encoding inside compatibility/infrastructure adapters; application code uses typed principals only.
24. Treat ACL `backend` mutation as reserved structured behavior handled by app/global access operations and the legacy mutation planner, not a generic named right.
25. Authorize ACL/group/membership mutations through application use cases inside the access-control UoW; never call ACL repositories directly from presentation.
26. Keep API credential storage/policy separate from API HTTP transport and method authorization; presentation must consume the credential use cases rather than query OAuth tables directly.

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
- auth/session slice passes contract/policy/directory/password/session/persistence/integration tests;
- persistent-login slice passes strategy/issuer/session-establishment/restore/characterization/integration tests;
- access-control slice passes contracts/evaluator/fallback/mutation-policy/authorization/group/membership/persistence/integration/characterization tests;
- runtime session-state provider selection passes registry/composition/architecture tests;
- API credential core passes contracts/policy/repository/UoW/issue/exchange/resolve/revoke/characterization/SQLite vertical-flow tests;
- every new architectural decision is reflected here.