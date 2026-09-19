# State Backend Providers + API OAuth2 Credential Core — Design Specification

Status: accepted and implemented
Date: 2026-09-15
Repository: `boltholds/gomazon-webasyst`
Base: `main` at `2fdda93c7aecb7f500825dd56c1c966a63ab03e9`

## 1. Goal

Add two ordered architectural slices:

1. remove the hard-coded in-process session-state implementation from auth composition and replace it with an extensible provider/factory/registry seam;
2. add a Webasyst 4.2.0-compatible API OAuth2 credential core over the existing `wa_api_auth_codes` and `wa_api_tokens` tables.

The first slice is a prerequisite for runtime-state portability. The second slice completes the remaining credential foundation needed before the HTTP/API framework can be ported.

The design preserves the existing architectural rules:

- application code depends on application-owned ports, not infrastructure implementations;
- expected negative outcomes use explicit typed variants, not `None`, `Optional`, empty values, or bool sentinels;
- cross-boundary contracts are Pydantic discriminated unions;
- closed serialized string domains use `EnumStr`; open extension identifiers such as `StateProviderName` remain open immutable values;
- infrastructure failures propagate unless an expected domain result explicitly models them;
- legacy storage conventions stay at compatibility/persistence boundaries;
- SQLAlchemy, FastAPI, Redis, Supabase, and other concrete technologies must not leak into application use cases.

## 2. Why the state-provider refactor comes first

The current application boundary is already correct: auth use cases depend on `SessionStateStore`.

The remaining coupling is in composition, where `auth.py` directly constructs `InMemorySessionStateStore()`.

That means replacing process-local memory with Redis, a Supabase/Postgres-backed implementation, or another distributed store does not require changing auth use cases, but it still requires editing the composition implementation itself.

This design removes that final hard-coded selection.

The requested "Prototype" behavior is implemented as an explicit provider/factory/registry seam rather than GoF `Prototype.clone()`. Cloning a state repository does not solve backend selection. The required behavior is:

- select a named provider at composition time;
- have the provider construct the concrete `SessionStateStore`;
- allow external registration of additional providers without changing auth/application code;
- keep one resolved store instance shared by the auth use cases in one application container.

This is effectively Port/Adapter + Strategy/Abstract Factory + Registry.

## 3. State-provider architecture

### 3.1 Domain port remains unchanged

`SessionStateStore` remains the application-owned contract:

```python
class SessionStateStore(Protocol):
    async def create(self, request: SessionCreateRequest) -> SessionCreationResult: ...
    async def resolve(self, session_id: SessionId) -> SessionStateResolution: ...
    async def revoke(self, key: AuthSessionKey) -> SessionRevocationResult: ...
```

No Redis, SQL, Supabase, serialization, connection-pool, or cache types appear here.

The existing domain-specific port is intentionally retained instead of replacing it with a generic `Repository[Any, Any]` or `MemoryRepository` abstraction.

### 3.2 Provider name is open, not an enum

Provider identifiers are extensible configuration values, so they are not a closed `EnumStr` domain.

Use an immutable value object such as:

```python
@dataclass(slots=True, frozen=True)
class StateProviderName:
    value: str
```

Empty names are rejected at construction/configuration normalization.

Examples include `memory`, `redis`, `supabase`, `dragonfly`, or an application-specific provider name.

### 3.3 Factory/provider contract

Composition owns a small factory contract:

```python
class SessionStateStoreFactory(Protocol):
    def create(self) -> SessionStateStore: ...
```

The first concrete factory is:

```python
class InMemorySessionStateStoreFactory:
    def create(self) -> SessionStateStore: ...
```

A future Redis adapter can register `RedisSessionStateStoreFactory`; a future Supabase/Postgres adapter can register `SupabaseSessionStateStoreFactory`.

Factories may own infrastructure configuration or clients, but application use cases only receive the resulting `SessionStateStore`.

### 3.4 Registry

Composition owns a registry of factories keyed by `StateProviderName`.

Conceptual API:

```python
class SessionStateProviderRegistry:
    def register(
        self,
        name: StateProviderName,
        factory: SessionStateStoreFactory,
    ) -> ProviderRegistrationResult: ...

    def resolve(
        self,
        name: StateProviderName,
    ) -> SessionStateProviderResolution: ...
```

Expected outcomes are explicit variants:

- provider registered;
- duplicate registration rejected;
- provider resolved;
- provider unknown.

The registry must not use `dict.get(...) -> None` as its public result contract.

### 3.5 Configuration and selection

Settings expose a provider name with `memory` as the default.

Conceptually:

```text
SESSION_STATE_PROVIDER=memory
```

Selection flow:

```text
settings
   |
   v
StateProviderName
   |
   v
SessionStateProviderRegistry
   |
   v
SessionStateStoreFactory
   |
   v
SessionStateStore
   |
   +--> AuthenticateBackendPassword
   +--> ResolveBackendSession
   +--> LogoutBackendSession
   +--> persistent-login restore
```

`composition/auth.py` must no longer import or construct `InMemorySessionStateStore` directly.

Default application composition may build a default registry containing the memory provider. Custom deployments may supply an augmented/replaced registry.

There must be no centralized `if provider == "redis" / elif provider == "supabase"` selector.

### 3.6 Store lifetime

One application container resolves exactly one `SessionStateStore` instance and passes that same instance to all auth/session use cases in that container.

The registry/factory creates stores; it does not create a fresh store per request or per use-case call.

For the in-memory provider this preserves session continuity within the process. Distributed providers naturally permit continuity across multiple application instances.

### 3.7 In-memory provider

`InMemorySessionStateStore` remains a concrete infrastructure adapter and remains the default.

Its externally relevant behavior stays:

- generated opaque session id;
- 30-minute inactivity TTL by default;
- resolve refreshes `last_seen_at`;
- expiry removes state;
- revoke is idempotent through explicit result variants;
- collision returns the existing typed creation error.

The provider/factory supplies its configurable clock, id factory, and TTL.

A reusable SessionStateStore contract suite must exercise the same behavioral contract against the memory adapter and future distributed adapters.

### 3.8 Future Redis provider

A Redis implementation is explicitly supported by the architecture but is not implemented in this slice.

Expected implementation characteristics:

- native key TTL for expiration;
- atomic create-if-absent for session-id collision safety;
- atomic resolve/touch semantics where required;
- explicit serialization at the infrastructure boundary;
- key namespace/version prefix owned by the adapter;
- no Redis result type crosses into application code.

Redis, KeyDB, or Dragonfly implementations must pass the same SessionStateStore contract suite.

### 3.9 Future Supabase provider

A future Supabase implementation must treat durable Postgres storage as the source of truth.

Supabase Realtime may be used for revocation/invalidation propagation or optional cache synchronization, but Realtime itself is not the authoritative key-value state store.

Conceptual deployment:

```text
instance A ----+
               |
               v
      Supabase/Postgres session rows
               |
               +---- Realtime revoke/invalidation event ---> instance B cache
               +---- Realtime revoke/invalidation event ---> instance C cache
```

A Python-owned session-state table would require an Alembic migration at the time this adapter is implemented. It is not part of the present slice.

## 4. Webasyst 4.2.0 API credential characterization

The supplied Framework 4.2.0 source is authoritative.

### 4.1 Authorization-code table

`wa_api_auth_codes` contains:

- `code varchar(32)` primary key, non-null;
- `contact_id int(11)`, non-null;
- `client_id varchar(32)`, non-null;
- `scope text`, non-null;
- `expires datetime`, non-null.

Legacy authorization code generation produces a 32-character MD5-shaped hex string and sets expiry to current time + 180 seconds.

Externally observable compatibility requirement: generated Python codes are 32 lowercase hex characters and expire after exactly 180 seconds by default.

The Python implementation should use a cryptographically secure generator such as `secrets.token_hex(16)` rather than reproducing PHP `md5(microtime(...).uniqid())`, because the exact entropy source is not an externally meaningful compatibility contract.

### 4.2 Access-token table

`wa_api_tokens` contains:

- `token varchar(32)` primary key, non-null;
- `contact_id int(11)`, non-null;
- `client_id varchar(32)`, non-null;
- `scope text`, non-null;
- `create_datetime datetime`, non-null;
- `last_use_datetime datetime`, nullable;
- `expires datetime`, nullable;
- unique `(contact_id, client_id)`.

Legacy token generation produces a 32-character hex token.

New Python-generated tokens should preserve that shape using a secure random generator.

### 4.3 Token issuance semantics

For a `(contact_id, client_id)` pair:

- if a token already exists, the same token is returned;
- if requested scope differs, the row scope is updated;
- a new token value is not rotated merely because scope changed;
- if no token exists, a new row is created;
- newly-created legacy-compatible tokens have no expiry (`expires = NULL`).

The unique `(contact_id, client_id)` constraint is part of the compatibility contract.

### 4.4 Authorization-code exchange semantics

`api.php/token` requires:

- `code`;
- `client_id`;
- `grant_type=authorization_code`.

Exchange behavior:

- unknown code -> invalid grant;
- mismatched client id -> invalid grant;
- expired code -> invalid grant;
- valid code -> issue/reuse API token using the code's contact/client/scope.

Important legacy quirk: the code row is not deleted or marked consumed after successful exchange. It remains reusable until expiry.

This behavior must be isolated behind a Webasyst compatibility policy so a future strict OAuth mode can consume codes once without changing the credential stores or use-case structure.

### 4.5 Token resolution semantics

Legacy token resolution:

- token may later be extracted from query/form input or `Authorization: Bearer`, but transport extraction is outside this slice;
- unknown token is invalid;
- expired non-null `expires` is invalid;
- a valid token updates `last_use_datetime`;
- the resulting principal is identified by `contact_id`;
- app-access and per-app scope checks happen after token validation in the API dispatch layer.

Therefore `ResolveApiAccessToken` validates credential state and touches usage, but does not itself implement API method authorization.

### 4.6 Revoke semantics

The credential core supports deletion by exact access token.

The application result is explicit:

- revoked;
- already missing.

Transport-specific oddities of the legacy revoke controller are deferred to the HTTP compatibility slice.

## 5. API credential values and contracts

### 5.1 Immutable values

Application values include:

- `AuthorizationCode`;
- `ApiAccessToken`;
- `ApiClientId`;
- `ApiScope`;
- reuse existing typed `AppId` for scope entries where appropriate.

`AuthorizationCode`, `ApiAccessToken`, and `ApiClientId` reject empty values.

Compatibility generators produce 32-character lowercase hexadecimal code/token values.

### 5.2 API scope

`ApiScope` is an immutable ordered tuple of app ids.

It must be non-empty for issuance.

It preserves deterministic order and does not expose the legacy comma-separated storage string to application use cases. The SQLAlchemy compatibility adapter serializes/deserializes the legacy comma-separated representation.

Duplicate app ids are normalized or rejected by one explicit policy; they must not be silently represented twice internally.

The chosen implementation should normalize to order-preserving uniqueness to match the effective behavior of the legacy approval action.

### 5.3 Token expiry is a state union, not `datetime | None`

Application contracts model token expiry explicitly:

```text
ApiTokenNeverExpires
ApiTokenExpiresAt(at)
```

Only the legacy ORM row may use `datetime | None` because the database column is genuinely nullable.

The persistence adapter normalizes SQL `NULL` immediately to `ApiTokenNeverExpires`.

### 5.4 Stored records

Cross-boundary Pydantic records represent:

`StoredAuthorizationCode`:

- code;
- contact id;
- client id;
- scope;
- expires at.

`StoredApiAccessToken`:

- token;
- contact id;
- client id;
- scope;
- created at;
- last-use state;
- expiry state.

Nullable `last_use_datetime` is also normalized to an explicit application state rather than leaking `None` beyond persistence.

## 6. API credential persistence boundary

### 6.1 Existing legacy tables remain authoritative

Unlike runtime session state, Webasyst OAuth credentials are already persistent legacy data.

The default compatibility implementation therefore maps and uses `wa_api_auth_codes` and `wa_api_tokens` directly through SQLAlchemy.

No new OAuth tables and no migration are introduced in this slice.

### 6.2 Ports

Application-owned repository ports are intent-oriented.

Conceptually:

```python
class AuthorizationCodeRepository(Protocol):
    async def create(...) -> AuthorizationCodeCreationResult: ...
    async def resolve(...) -> AuthorizationCodeResolution: ...
    async def delete(...) -> AuthorizationCodeDeletionResult: ...

class ApiTokenRepository(Protocol):
    async def resolve(...) -> ApiTokenResolution: ...
    async def find_for_subject_client(...) -> ApiTokenSubjectClientLookup: ...
    async def create(...) -> ApiTokenCreationResult: ...
    async def update_scope(...) -> ApiTokenScopeUpdateResult: ...
    async def touch_last_use(...) -> ApiTokenTouchResult: ...
    async def revoke(...) -> ApiTokenRevocationResult: ...
```

Every expected lookup miss is an explicit variant.

### 6.3 Dedicated unit of work

Credential operations use a dedicated `ApiCredentialUnitOfWork` exposing the two repositories and explicit commit/rollback/lifecycle behavior.

This prevents transaction coordination from leaking SQLAlchemy upward and allows token issue/reuse to remain atomic with respect to the unique `(contact_id, client_id)` rule.

Infrastructure constraint violations that represent a known token collision may be normalized to a typed collision result. Unexpected database failures propagate.

## 7. Credential policies

### 7.1 Token generator

Application depends on a token/code generator port rather than directly calling `secrets`.

The default compatibility generator uses secure 16-byte random values rendered as 32 lowercase hex characters.

Deterministic generators can be supplied in tests.

### 7.2 Authorization-code exchange policy

A policy isolates the legacy reusable-code quirk.

Conceptual result on successful validation:

```text
KeepAuthorizationCode
ConsumeAuthorizationCode
```

The Webasyst 4.2.0 policy returns `KeepAuthorizationCode`.

A future strict OAuth policy may return `ConsumeAuthorizationCode` without changing the repositories or exchange use case.

### 7.3 Token issue/reuse policy

The compatibility policy preserves Webasyst behavior:

- lookup by `(contact_id, client_id)`;
- existing -> keep token value, update scope only when changed;
- missing -> generate token and insert with never-expires state.

This behavior is isolated enough that a future rotating-token issuer can be introduced without changing token resolution.

## 8. Application use cases

### 8.1 IssueAuthorizationCode

Input:

- authenticated backend subject/contact id;
- client id;
- already-approved non-empty API scope.

Behavior:

1. generate a code;
2. set expiry to `now + 180 seconds` under the compatibility lifetime policy;
3. persist the authorization-code record;
4. return an explicit issued result.

This credential-core slice does not decide which requested apps the user consents to. It accepts an already-approved scope. No HTTP route may expose this use case directly until the next API authorization/consent layer performs installed-app and ACL scope filtering.

### 8.2 ExchangeAuthorizationCode

Input:

- authorization code;
- client id.

Behavior:

1. resolve code;
2. reject missing code;
3. reject client mismatch;
4. reject expired code;
5. issue/reuse access token for the code's contact/client/scope;
6. apply exchange disposition policy (`KeepAuthorizationCode` for Webasyst compatibility);
7. commit;
8. return access token result.

### 8.3 IssueImplicitApiAccessToken

Supports the credential operation behind legacy `response_type=token` without implementing its HTTP redirect flow.

Input:

- authenticated backend subject/contact id;
- client id;
- already-approved scope.

Behavior:

- issue/reuse access token through the same token policy used by code exchange.

### 8.4 ResolveApiAccessToken

Input:

- exact `ApiAccessToken`.

Behavior:

1. resolve token;
2. reject unknown token;
3. reject expired token;
4. update `last_use_datetime` to current time;
5. return token principal, client id, scope, and expiry state.

It does not check requested API app or method permissions. That belongs to API request authorization.

### 8.5 RevokeApiAccessToken

Input:

- exact `ApiAccessToken`.

Behavior:

- delete the row if present;
- return explicit `revoked` or `already_missing` result.

## 9. Scope authorization boundary for the next slice

Legacy `api.php/auth` filters requested scope by:

- installed application existence;
- current authenticated backend user's `backend` right for each app.

That layer also handles login, CSRF, approve/deny UI, redirect construction, and implicit/code response type behavior.

Those responsibilities are intentionally not added to the credential core.

The next API framework/authorization slice will introduce the minimum installed-app directory/catalog port and will reuse the existing access-control subsystem to produce an approved `ApiScope` before calling `IssueAuthorizationCode` or `IssueImplicitApiAccessToken`.

This keeps credential storage independent from UI/transport/app discovery.

## 10. Composition

### 10.1 Session state

Auth composition is refactored so `_create_auth_foundation` receives a resolved `SessionStateStore` rather than constructing memory internally.

A higher composition layer:

1. reads state-provider settings;
2. resolves factory from registry;
3. creates one store instance;
4. passes that instance into auth composition.

A test/custom composition entry point may inject a `SessionStateStore` directly.

### 10.2 API credentials

API credential composition constructs:

- SQLAlchemy `ApiCredentialUnitOfWorkFactory` over the existing Webasyst schema;
- secure token/code generator;
- Webasyst code-lifetime/exchange policy;
- Webasyst token issue/reuse policy;
- issue/exchange/resolve/revoke use cases.

No FastAPI route is mounted in this slice.

## 11. Error model

Expected state-provider outcomes:

- unknown provider;
- duplicate provider registration.

Expected authorization-code outcomes:

- code issued;
- collision;
- code missing;
- code expired;
- client mismatch.

Expected token outcomes:

- token issued new;
- token reused;
- token missing;
- token expired;
- token revoked;
- token already missing;
- token collision where meaningfully recoverable.

These are typed results.

Unexpected Redis/SQLAlchemy/network/driver failures are not converted into `NOT_FOUND`, `INVALID_TOKEN`, or other expected-domain results.

## 12. Concurrency and atomicity

### 12.1 In-memory sessions

The in-memory implementation must provide atomic process-local create/resolve/revoke transitions sufficient to prevent inconsistent mutation when async tasks interleave.

An internal lock is acceptable and remains infrastructure-private.

### 12.2 API tokens

The database unique key `(contact_id, client_id)` is authoritative.

Issue/reuse runs in one credential UoW transaction. Concurrent first issuance must not create two durable tokens for one pair.

The adapter/use case may retry or re-read after a recognized unique-key race, but must not swallow unrelated integrity failures.

### 12.3 Authorization codes

Code generation handles rare primary-key collision through explicit retry/collision policy with a bounded attempt count; it must not loop forever.

## 13. Security decisions

- New generated codes/tokens use cryptographically secure randomness while preserving 32-hex compatibility shape.
- Raw token values must not be logged on validation failures; hashes/fingerprints may be logged by later presentation/observability layers.
- Authorization-code reusability is preserved only in the Webasyst compatibility policy and documented as a legacy behavior.
- New application code must not infer authorization merely from possession of a valid API token; app ACL and scope are checked in the API authorization layer.
- A token with `expires = NULL` is represented explicitly as never expiring, not as missing state.

## 14. Testing strategy

### 14.1 State-provider tests

Unit tests cover:

- provider-name validation;
- register/resolve;
- duplicate registration;
- unknown provider;
- default memory provider;
- custom provider injection;
- one store instance shared across assembled auth use cases;
- `composition/auth.py` no longer directly constructs/imports the concrete memory store.

A reusable SessionStateStore contract suite covers:

- create;
- collision;
- resolve;
- inactivity refresh;
- expiry;
- revoke;
- wrong-key revoke;
- idempotent missing revoke.

The existing in-memory adapter must pass the suite.

### 14.2 Webasyst characterization tests

Pin exact 4.2.0 behavior:

- auth code length/shape and 180-second TTL;
- auth code table fields;
- token table fields and nullable columns;
- unique `(contact_id, client_id)`;
- token reuse;
- scope update without rotation;
- default never-expiring token;
- code not consumed after exchange;
- valid token touch of `last_use_datetime`.

### 14.3 OAuth unit tests

Cover all explicit negative variants, generator injection, expiry state unions, code-client mismatch, code reuse, token reuse, token scope update, token expiry, touch, and revoke.

### 14.4 SQLAlchemy integration

SQLite integration tests map the legacy tables and run a vertical flow:

1. issue authorization code;
2. exchange it;
3. exchange same still-valid code again and receive same token;
4. change scope through a subsequent issue path and confirm token reuse + scope update;
5. resolve token and confirm `last_use_datetime` update;
6. revoke token;
7. resolve again and receive typed missing/invalid result.

Also test expiry and rollback behavior.

### 14.5 Architecture guards

Add guards ensuring:

- application credential files do not import SQLAlchemy/FastAPI/Redis/Supabase;
- auth composition does not hard-code `InMemorySessionStateStore`;
- expected credential/state results do not introduce optional-result sentinels;
- raw legacy comma-scope serialization stays outside application use cases.

## 15. Non-goals

This slice does not implement:

- Redis client integration;
- Supabase/Postgres session-state adapter;
- Supabase Realtime listeners;
- FastAPI OAuth routes;
- `api.php/auth`, `api.php/token`, or `api.php/revoke` transport compatibility;
- Bearer/query/form access-token extraction;
- consent HTML or CSRF handling;
- redirect URI construction;
- installed-app catalog/discovery;
- API method dispatch;
- per-method rights;
- JSON/XML/JSONP decorators;
- client registration or client-secret validation not present in this legacy flow;
- Webasyst ID headless token exchange;
- social OAuth login providers;
- token hashing-at-rest schema redesign;
- replacement of legacy OAuth tables.

## 16. Implementation order

The implementation plan should preserve this sequence:

### Milestone A — session state provider seam

1. provider values/results/contracts;
2. provider factory + registry;
3. memory factory;
4. settings/composition integration;
5. reusable SessionStateStore contract tests;
6. refactor auth composition to injected state store;
7. architecture guard against direct concrete-store selection.

### Milestone B — API OAuth2 credential core

1. source characterization tests;
2. values/enums/Pydantic result contracts;
3. legacy ORM mappings;
4. repository/UoW ports and SQLAlchemy adapters;
5. secure generator and compatibility policies;
6. issue/exchange/implicit/resolve/revoke use cases;
7. composition;
8. SQLite vertical flow;
9. architecture guards and full-suite verification.

The state-provider seam is completed and green before OAuth credential implementation begins.

## 17. Planned architecture decisions

Implementation should record the accepted decisions in `AGENTS.md` as new ADRs, without renumbering existing ADRs:

- session state backend selection belongs to composition through an extensible provider/factory/registry; domain-specific `SessionStateStore` remains the application port;
- generic state repositories do not replace domain-specific application ports;
- legacy API OAuth credentials remain in `wa_api_auth_codes` / `wa_api_tokens` and are not moved to the runtime state backend;
- API authorization codes retain Webasyst reusable-until-expiry behavior only through a compatibility policy;
- API token never-expiring state and never-used state are explicit unions outside nullable ORM fields.

## 18. Completion criteria

The combined slice is complete when:

- auth composition no longer directly selects the memory implementation;
- default runtime behavior still uses in-memory sessions and all existing auth tests remain green;
- a custom session-state factory/provider can be registered and selected without changing application/auth code;
- the architecture can accept future Redis and Supabase providers through the same seam;
- exact legacy `wa_api_auth_codes` and `wa_api_tokens` mappings are present;
- authorization code issue/exchange semantics match characterized Webasyst behavior;
- token issue/reuse/scope-update semantics match Webasyst behavior;
- access-token resolution handles expiry and updates last-use time;
- revoke is explicit and idempotent;
- no OAuth HTTP route has been mounted prematurely;
- architecture and Optional/nullability guards pass;
- full test suite and `compileall` pass on the feature branch.
