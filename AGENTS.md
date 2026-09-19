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
- API execution core design: `docs/superpowers/specs/2026-09-19-api-execution-core-design.md`
- Backend session HTTP bridge design: `docs/superpowers/specs/2026-09-19-backend-session-http-bridge-design.md`
- OAuth authorization surface design: `docs/superpowers/specs/2026-09-19-oauth-authorization-surface-design.md`
- Installed application registry/discovery design: `docs/superpowers/specs/2026-09-19-installed-application-registry-discovery-design.md`
- Installed application registry/discovery plan: `docs/superpowers/plans/2026-09-19-installed-application-registry-discovery.md`
- Application runtime/events/plugins design: `docs/superpowers/specs/2026-09-19-application-runtime-events-plugins-design.md`
- Application runtime/events/plugins plan: `docs/superpowers/plans/2026-09-19-application-runtime-events-plugins.md`
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
### ADR-035 — API Execution Core code is classified as Entity, VO, Service, or Composite
Status: accepted
Date: 2026-09-19

Every new API Execution Core domain/application type MUST have one explicit responsibility category: Entity, Value Object, Service, or Composite. Entities carry stable domain identity; VOs are immutable validated equality-by-value values; Services own one coherent rule/operation; Composites orchestrate already-defined entities/VOs/services without becoming service locators or hiding primitive business rules. This taxonomy operates inside the existing application/contracts/ports/infrastructure/presentation dependency boundaries and does not replace them. SQLAlchemy rows and HTTP adapters are infrastructure/presentation types, not domain Entities. New API Execution Core code that cannot be classified cleanly is an architecture smell and must be redesigned before merge.

### ADR-036 — API method execution is a typed staged Composite pipeline
Status: accepted
Date: 2026-09-19

Webasyst-compatible API execution is normalized into one `ApiExecutionPipeline` Composite. Observable authorization order is preserved: resolve credential -> update compatibility activity -> installed app -> app access -> token scope -> license -> method registry -> HTTP method validation -> handler execution. Expected negative outcomes are typed variants and stop later stages. The pipeline owns sequencing only and MUST NOT contain SQL, FastAPI/Starlette request objects, response formatting, dynamic imports, access-right calculations, or handler-specific parameter parsing.

### ADR-037 — API methods are registered Entities; legacy transport stays at compatibility boundaries
Status: accepted
Date: 2026-09-19

PHP class-name construction and `class_exists()` lookup are replaced by an application-owned `ApiMethodRegistry` keyed by open `ApiMethodTarget`/`ApiMethodName` VOs and returning registered `ApiMethodDefinition` Entities. Adding a method requires registration, not a central dispatch branch or dynamic import. HTTP method tokens are open uppercase VOs; closed response/result/rejection domains use `EnumStr`. Query/form source distinction, Bearer/request-token extraction, JSON/XML/JSONP rendering, legacy error envelopes, API-disable behavior and HTTPS redirects remain compatibility/presentation concerns and MUST NOT leak into application method handlers.


### ADR-038 — Backend HTTP authentication returns credential dispositions, not cookie operations
Status: accepted
Date: 2026-09-19

The backend-session HTTP bridge is transport-neutral at the application boundary. Its Composites return explicit `IssueSessionCredential | ClearSessionCredential | KeepSessionCredential` session intents and reuse `RefreshPersistentCredential | ClearPersistentCredential | KeepPersistentCredential` for persistent authentication. FastAPI/Starlette cookie reads/writes, cookie names, SameSite/Secure attributes and expiry headers remain presentation/composition concerns. Password authentication, session resolution, persistent restore and logout continue to use the existing auth use cases; no second authentication system or global current-user object is introduced.

### ADR-039 — Python backend sessions use an opaque native cookie and do not impersonate PHP sessions
Status: accepted
Date: 2026-09-19

The Python rewrite transports the existing opaque `SessionId` in a dedicated host-only backend cookie, default name `gomazon_session`. It is not named `PHPSESSID`, does not decode PHP session files, and does not claim interoperability with PHP `$_SESSION`. Runtime `SessionStateStore` state remains authoritative for expiry/revocation. The legacy persistent credential continues to use the compatibility cookie name `auth_token`. PHP session interoperability, if needed later, must be a separate compatibility adapter.

### ADR-040 — Browser current-subject resolution is session-first with persistent-login fallback
Status: accepted
Date: 2026-09-19

Browser-authenticated surfaces resolve identity in a fixed order: valid Python session credential first; only if no subject is resolved may the bridge attempt persistent-login restoration. A valid session always wins and persistent restore is not invoked. A rejected supplied session credential is scheduled for clearing. If persistent login is globally disabled, persistent restore is not invoked and existing `auth_token` transport is left untouched. Session-only password login also leaves an existing persistent credential untouched. Logout is idempotent and clears both session and persistent credential transport.


### ADR-041 — Webasyst OAuth authorization is a separate typed surface over existing auth and credential cores
Status: accepted
Date: 2026-09-19

`/api.php/auth`, `/api.php/token`, and `/api.php/revoke` form a dedicated OAuth authorization surface. The authorization application layer owns typed consent/grant orchestration and reuses `BackendCurrentSubjectFlow`, `BackendPasswordLoginFlow`, `BackendLogoutFlow`, `IssueAuthorizationCode`, `IssueImplicitApiAccessToken`, `ExchangeAuthorizationCode`, `ResolveApiAccessToken`, and `RevokeApiAccessToken`. It MUST NOT query session/token tables directly or receive FastAPI/Starlette Request objects. Browser/HTTP behavior, CSRF, HTML, JSON/XML envelopes and Webasyst quirks remain compatibility/presentation concerns.

### ADR-042 — Legacy unregistered redirect behavior is isolated behind an OAuth redirect policy
Status: accepted
Date: 2026-09-19

Webasyst 4.2.0 does not maintain an OAuth client registry and accepts request-supplied `client_id`, `client_name`, and `redirect_uri`. Exact compatibility therefore uses an injected `OAuthRedirectPolicy`; the first `LegacyUnregisteredRedirectPolicy` preserves request-supplied redirects. Application orchestration MUST NOT assume that unregistered redirects are intrinsically valid. A future registered-client policy may validate client/redirect pairs without changing credential storage or authorization Composites.

### ADR-043 — Revoke authentication credential and revoke target are distinct compatibility states
Status: accepted
Date: 2026-09-19

For `/api.php/revoke`, outer API authentication follows normal legacy credential precedence (request token, Authorization header, server `HTTP_AUTHORIZATION`), but the controller separately reads only request-level `access_token` as the deletion target. Compatibility therefore models `RevokeTargetProvided | RevokeTargetMissing` separately from the authenticated credential. Header-only Bearer authentication succeeds but produces a no-op deletion and `{"access_token": ""}`; no invalid empty `ApiAccessToken` is constructed and the generic revocation use case remains strict.

### ADR-044 — Legacy token/revoke controllers use HTTP 200 payload errors and no JSONP
Status: accepted
Date: 2026-09-19

`/api.php/token` and controller-level `/api.php/revoke` responses preserve Webasyst 4.2.0 controller semantics: ordinary success/error payloads are HTTP 200, response format is JSON by default with optional XML, invalid explicit format becomes JSON `invalid_request`, and JSONP is not applied. Framework-level precondition/authentication failures that happen before those controllers keep their own HTTP statuses.

### ADR-045 — Installed application identity and metadata come from one canonical shared catalog
Status: accepted
Date: 2026-09-19

Runtime-installed application identity is represented by one application-owned `InstalledApplicationCatalog` shared by production composition. Webasyst compatibility discovery normalizes `wa-config/apps.php` plus per-app `lib/config/app.php` metadata into immutable `InstalledApplication` Entities/VOs; raw PHP arrays, filesystem paths and parser types do not cross into application code. API Execution consumes the canonical catalog for app-existence authorization, while OAuth consent uses a consumer-specific projection over the same catalog for display metadata. `ApiMethodRegistry` and `DispatchRegistry` remain separate registries because installation, executable API methods and dispatch handlers are distinct concepts. The first implementation uses one startup snapshot per container and does not execute arbitrary PHP, perform request-time filesystem discovery, or recreate `waSystem` as a service locator.


### ADR-046 — Canonical installed-app metadata is locale-neutral and excludes legacy build cache state
Status: accepted
Date: 2026-09-19

Webasyst 4.2.0 `waSystem::getApps()` translates application/header-item names and caches loaded app info per locale, while also injecting a `build` value from `build.php`, debug time, or zero. The Python runtime intentionally constructs one shared installed-application snapshot per Container, so that canonical snapshot MUST NOT capture a request/user locale or cache-busting build value. `InstalledApplication` stores the raw manifest default name plus normalized static metadata; locale-specific names belong to a later consumer projection/localization boundary. Until that projection exists, OAuth consent may display the manifest default name and MUST NOT be described as having localized UI parity. Legacy build metadata is omitted until a concrete consumer requires it.


### ADR-047 — Installed metadata and executable Python runtime are separate truths
Status: accepted
Date: 2026-09-19

`InstalledApplicationCatalog` and the new `InstalledPluginCatalog` describe what the legacy Webasyst installation says is installed/enabled. They MUST NOT contain executable Python callables, service instances, dynamically imported classes, or request-time state. Executable behavior is declared separately through explicit immutable `ApplicationRuntimeModule` and `PluginRuntimeModule` values assembled in composition. An installed app/plugin is not executable in Python until its runtime module is explicitly linked; a runtime module for an app/plugin that is not installed/enabled is invalid composition.

### ADR-048 — Event dispatch uses explicit handler definitions and preserves legacy ordering/first-result semantics
Status: accepted
Date: 2026-09-19

PHP handler-file scanning, class-name derivation and `class_exists()` execution are replaced by an application-owned `EventHandlerRegistry` of explicit `EventHandlerDefinition` Entities. Event identity is `EventKey(AppId, EventName)`; source-app selection and event-name patterns use typed variants rather than magic `*` strings. Matching preserves Webasyst 4.2.0 bucket precedence: exact app/exact event -> exact app/masked event -> any app/exact event -> any app/masked event, with registration order preserved inside each bucket. Only the first non-empty result per application/plugin result owner is retained; a no-result outcome leaves that owner eligible. Handler failures are diagnosed and dispatch continues, matching legacy non-fatal handler behavior.

### ADR-049 — Application runtime linking is a startup validation step, not a service locator or hot-loader
Status: accepted
Date: 2026-09-19

A single `ApplicationRuntimeLinker` validates all Python runtime declarations against canonical installed application/plugin catalogs before populating the existing dispatch/API registries and the new event registry. Validation completes before live registries are mutated so duplicate/foreign registrations fail composition instead of leaving a partial runtime. Runtime modules are imported only through explicit Python composition code; request/app/plugin strings MUST NOT select modules or classes. The first runtime graph is immutable after startup; live plugin/app enable/disable, import scanning, PHP execution, cron scheduling and installer-driven hot reload are later slices.

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
    api_execution/
      entities/
      vo/
      services/
      composites/
    oauth_authorization/
      entities/
      vo/
      services/
      composites/
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

## Backend session HTTP bridge rules

- backend browser authentication uses the existing auth/session/persistent-login use cases; no parallel auth model is introduced;
- bridge application code is classified as VO, Service, or Composite; existing `AuthenticatedSubject`/`AuthSessionKey`/`StoredAuthSession` remain the identity-bearing entities and MUST NOT be duplicated;
- valid Python session credential wins over persistent credential fallback;
- supplied rejected session credentials return explicit clear-session transport intent;
- persistent-login disabled means no restore attempt and no mutation of existing `auth_token`;
- session-only password login MUST NOT clear or rotate an existing persistent credential;
- remember intent is a closed typed value and MUST NOT be added as `remember: bool` to `BackendPasswordCredentials`;
- cookie names, HttpOnly/SameSite/Secure/path/lifetime and Set-Cookie operations remain presentation/composition concerns;
- default Python session cookie is `gomazon_session`; default persistent cookie remains `auth_token`;
- Python session transport MUST NOT use `PHPSESSID` or decode PHP session files in this slice;
- no standalone production login route is mounted by this bridge; the next OAuth authorization slice consumes it.

---

## OAuth authorization surface compatibility rules

- `/api.php/auth` resolves browser identity only through the backend session HTTP bridge; OAuth code MUST NOT read session storage or authentication tables directly;
- authorization query requires `client_id`, `client_name`, `response_type`, and `scope`; `response_type=token` additionally requires `redirect_uri`;
- required legacy parameters use PHP-falsy compatibility semantics at the boundary;
- outer POST `cancel` executes before authentication and CSRF, and remains distinct from authenticated consent denial;
- backend login, authenticated approve/deny, and OAuth-surface logout use explicit CSRF handling outside auth credential use cases;
- requested scope is filtered through `OAuthConsentAppCatalog` plus `OAuthConsentAccessPolicy`; absent/unauthorized apps are silently omitted and empty effective scope is invalid;
- `OAuthConsentApplication` is the consent-screen Entity identified by `AppId`; client ids/names are request VOs, not registered client Entities in this compatibility slice;
- consent access uses ordinary backend access semantics and MUST NOT reuse the API execution `webasyst` access exception implicitly;
- code grants may display the authorization code when no redirect URI is supplied; implicit token grants always redirect via URI fragment;
- legacy request-supplied redirects are accepted only through `LegacyUnregisteredRedirectPolicy`;
- `/api.php/token` reads required fields from POST only and maps credential exchange failures to legacy payload codes;
- token/revoke controller payload errors use HTTP 200, JSON default/optional XML, invalid format -> JSON `invalid_request`, and no JSONP;
- revoke authentication credential and request-level revoke target are separate typed states; header-only Bearer revoke authenticates but performs a no-op deletion and returns an empty access-token value;
- static OAuth routes MUST be mounted before generic `/api.php/{api_path:path}` method execution;
- `token-headless`, Webasyst ID/social auth, registered clients, PKCE, refresh tokens, OIDC, license-cache/profile-update/cron are out of this slice.

---

## Installed application registry compatibility rules

- `wa-config/apps.php` plus normalized per-app `lib/config/app.php` metadata are the compatibility source for runtime-installed application identity;
- the framework `webasyst` application is a special system identity and must be characterized against the supplied 4.2.0 source rather than treated as an ordinary optional app entry;
- one `InstalledApplicationCatalog` instance is shared by API Execution and OAuth consent production composition;
- expected app lookup miss is an explicit typed result, never `None`, `False`, or an empty metadata bag;
- application registry Entity/VO state is immutable and does not expose filesystem paths, raw PHP arrays, parser nodes, routers, handlers, repositories, sessions, or service instances;
- API method registration and dispatch registration remain separate from installation discovery;
- OAuth consent metadata is projected from the canonical installed app entity; the characterized `webasyst` settings-header icon rule remains in the Webasyst OAuth compatibility projector;
- production discovery uses a configured Webasyst root and a restricted declarative PHP return-array parser; arbitrary PHP evaluation or subprocess execution is forbidden;
- the first implementation builds one startup snapshot per container; installer-driven hot reload is a later slice behind the same catalog port;
- malformed installation config is a configuration/infrastructure failure and must not be silently converted into an app-missing authorization result.
- exact discovery characterization is pinned to Webasyst Framework 4.2.0 release commit `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`;
- missing `wa-config/apps.php` is a startup/configuration failure; an enabled configured app with a missing manifest is omitted;
- configured app enablement follows characterized PHP truth semantics, and the legacy WAID rule may force-enable Installer through a compatibility settings/policy seam;
- `webasyst` is forced into the system-inclusive catalog and resolves from `wa-system/webasyst/lib/config/app.php`;
- canonical names remain locale-neutral raw manifest names; locale-specific translation is a later projection and localized OAuth UI parity is not claimed in this slice;
- legacy `build` metadata is intentionally excluded from the first Entity because current API/OAuth consumers do not require it;

---

## Application runtime / events / plugins compatibility rules

- installed app/plugin metadata and executable Python runtime declarations are separate; discovery never implies execution;
- enabled plugins are discovered from `wa-config/apps/<app_id>/plugins.php` plus `wa-apps/<app_id>/plugins/<plugin_id>/lib/config/plugin.php`, using the restricted declarative PHP parser only;
- missing plugin config is skipped and falsy plugin entries are disabled, matching characterized 4.2.0 behavior;
- legacy plugin capability flags normalize implicit event declarations: `rights -> rights.config`, `frontend -> routing`, and event discovery may add `cron -> cron`;
- plugin manifest handler declarations are migration inventory only; they MUST NOT dynamically import/execute PHP or Python classes;
- Python application/plugin runtime modules explicitly declare API, dispatch and event contributions and are linked only during startup composition;
- event identity is `EventKey(AppId, EventName)`; event source selectors and name patterns are typed variants, not `None` or magic sentinel fields;
- event matching preserves legacy exact/masked source/name bucket order and registration order;
- event dispatch retains only the first non-empty result per application/plugin owner while allowing later handlers after no-result outcomes;
- handler exceptions are recorded as diagnostics and do not abort unrelated handlers by default;
- compatibility result-key formatting and `array_keys` padding remain Webasyst adapters, not event-core rules;
- raw PCRE event patterns are isolated behind a compatibility matcher boundary and MUST NOT become arbitrary unbounded regex evaluation in application code;
- installed-but-unmigrated apps/plugins remain visible in catalogs but non-executable;
- plugin install/update/uninstall, settings UI, templates/assets, widgets, cron execution, CLI execution and live runtime reload are out of the first runtime slice.

---

## API execution compatibility rules

- all new API Execution Core domain/application code is organized explicitly under Entity, VO, Services, or Composite;
- `ApiMethodDefinition` is the registered method Entity and is identified by `ApiMethodTarget`;
- `ApiMethodName`, `AppId`, and `ApiHttpMethod` remain open VOs; closed framework state/result/format domains use `EnumStr`;
- the execution Composite reuses `ResolveApiAccessToken` and never queries `wa_api_tokens` directly;
- legacy authorization order is app exists -> app access -> scope -> license -> method lookup -> HTTP method validation -> execute;
- the `webasyst` backend-access exception is isolated behind `ApiAppAccessPolicy`, not hard-coded in the pipeline;
- dynamic PHP method class discovery is replaced by explicit `ApiMethodRegistry` registration;
- query and form parameters remain distinct through `ApiRequestParameters`;
- legacy required-parameter falsy behavior is isolated in a compatibility parameter-reader Service;
- JSON/XML/JSONP formatting and framework error envelopes stay outside application execution;
- an invalid explicit legacy `format` value returns `invalid_request` with HTTP 200, matching the 4.2.0 response call that omits an error status;
- presentation constructs `LegacyApiHttpRequestComposite` once and preserves credential precedence through request input, normal Authorization header, then server `HTTP_AUTHORIZATION` fallback;
- JSON recursively removes `_element`; XML preserves characterized `_element`/list/plural semantics; JSONP forces status 200 in the legacy adapter;
- API user `last_datetime` compatibility touch is a separate Service with the characterized >30 second threshold;
- `/api.php/auth` consent/redirect/CSRF remains a later slice.

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
- canonical installed-application identity/metadata is now available through `InstalledApplicationCatalog`; ACL mutation-time installation validation is still a separate consumer integration and must use that catalog rather than inventing another app source;
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
27. Classify all API Execution Core domain/application code explicitly as Entity, VO, Service, or Composite; keep application-owned ports separate from that taxonomy.
28. Resolve API methods only through explicit `ApiMethodRegistry` registration; never construct/import handler classes from request strings.
29. Keep API transport normalization and JSON/XML/JSONP rendering outside application execution; handlers receive typed context/parameters, never HTTP/ORM objects.
30. Resolve runtime-installed application identity/metadata through the canonical `InstalledApplicationCatalog`; do not introduce consumer-owned production app universes.
31. Parse legacy PHP application configuration only through the restricted compatibility parser; never evaluate arbitrary PHP or derive executable Python imports from app/request strings.
32. Keep installed app/plugin metadata separate from executable runtime modules; discovery MUST NOT auto-register handlers or Python imports.
33. Link application/plugin runtime contributions only through the startup `ApplicationRuntimeLinker` after full validation against installed catalogs.
34. Resolve events only through explicit `EventHandlerRegistry` definitions and preserve characterized handler ordering/first-result behavior; never scan/execute PHP handlers at request time.

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
- installed application registry/discovery slice is verified complete: exact 4.2.0 characterization is pinned to release commit `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`, obsolete duplicate app directories are removed, API/OAuth share one canonical catalog, and the completion head passed full CI with 693 tests;
- every new architectural decision is reflected here.