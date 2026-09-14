# Persistent Login / Remember-Me Compatibility Design

Status: proposed, user-approved in chat
Date: 2026-09-14
Target: Webasyst Framework 4.2.0 compatibility
Branch: `feature/persistent-login`

## Goal

Add backend persistent-login support on top of the existing password-auth/session foundation while preserving Webasyst 4.2.0 `auth_token` behavior and keeping the Python core open to a future opaque server-side token format.

The slice must not make the legacy deterministic MD5-derived token the permanent application contract. Legacy token parsing/generation belongs to a compatibility strategy. Application use cases operate on typed persistent-credential contracts and explicit outcomes.

## Source-backed Webasyst 4.2.0 behavior

The supplied 4.2.0 source is authoritative for this slice.

`waAuth::_remember()`:

- persistent login is available only when auth configuration enables remember-me;
- when login explicitly requests remember-me and it is enabled, Webasyst sets `auth_token` to `waAuth::getToken($user_info)`;
- `auth_token` expires after `2592000` seconds (30 days);
- legacy `auth_token` is set HttpOnly;
- a separate `remember` cookie is set to `1` for UI form preference;
- when remember-me is not requested, `_remember()` sets only `remember=0`; it does not generally revoke an existing `auth_token`.

`waAuth::_authByCookie()`:

- cookie authentication is attempted only when remember-me is enabled and an `auth_token` cookie is present;
- contact id is read from the characters between the first 15 and last 15 token characters;
- the contact is loaded by id;
- backend authentication requires an enabled backend user;
- the supplied token must exactly equal `getToken(user_info)`;
- a successful cookie restore renews `auth_token` for another 30 days using the same token value;
- an invalid/stale token clears `auth_token`;
- no dedicated remember-token database table participates in this algorithm.

`waAuth::getToken()`:

```text
hash = md5(create_datetime + login + password_hash)
auth_token = first_15_hex(hash) + decimal_contact_id + last_15_hex(hash)
```

Changing login, password hash, create datetime, or the contact id therefore changes the expected credential and invalidates an old cookie.

`waAuth::clearAuth()`:

- destroys current auth session state;
- clears `auth_token` when present;
- the separate `remember` UI-preference cookie is not the authentication credential.

`waAuth::updateAuth()`:

- if an `auth_token` cookie exists, Webasyst recomputes the credential from current contact data and refreshes the cookie for another 30 days.

## Scope

This slice includes:

- a typed persistent-credential value object;
- an extensible resolver-strategy chain for accepting persistent credentials;
- a separately injected issuer for the credential format currently emitted;
- exact legacy `auth_token` acceptance and issuance;
- persistent credential issuance after an already successful authentication;
- backend session restore from a persistent credential;
- refresh/clear/keep transport directives as typed application outcomes;
- reuse of the existing session state, active-auth registry and credential-version token infrastructure;
- source-backed characterization tests for legacy token format, expiry renewal semantics and invalidation behavior;
- composition wiring selecting the legacy strategy/issuer initially.

This slice does not include:

- a production login HTTP endpoint or cookie middleware;
- a new persistent-token database table;
- opaque v2 token issuance/storage;
- OAuth/social/Webasyst ID;
- OTP;
- frontend signup/confirmation;
- groups/permissions;
- API OAuth2 tokens;
- browser UI for the remember checkbox;
- PHP session-file interoperability.

## Architectural invariants

Existing ADRs remain mandatory:

- expected negative outcomes are explicit typed results, never `None`, bool sentinels or empty values;
- `Optional` is reserved for genuine external nullability;
- discriminators use `EnumStr` domains;
- internal value objects use `@dataclass(slots=True, frozen=True)` where wire validation is not needed;
- extensible behavior uses registries/strategies rather than one method per format;
- Webasyst-specific token mechanics stay in compatibility adapters;
- application code does not import `hashlib`, cookie/HTTP types, SQLAlchemy or compatibility implementations.

## Persistent credential value objects

The raw credential and lifetime are opaque internal value objects:

```python
from datetime import timedelta

@dataclass(slots=True, frozen=True)
class PersistentCredential:
    value: str

@dataclass(slots=True, frozen=True)
class PersistentCredentialLifetime:
    value: timedelta
```

The legacy adapter supplies `timedelta(days=30)`. Application code does not repeat the raw `2592000` constant.

Legacy parsing produces a compatibility-private value object:

```python
@dataclass(slots=True, frozen=True)
class LegacyAuthTokenCredential:
    contact_id: int
    credential: PersistentCredential
```

The application layer never depends on `LegacyAuthTokenCredential`.

## Resolver strategy model

A raw cookie has no explicit scheme prefix in Webasyst 4.2.0, so acceptance cannot be a simple dictionary lookup by scheme. The resolver uses an ordered strategy chain.

Application-owned strategy protocol:

```python
class PersistentCredentialStrategy(Protocol):
    async def resolve(
        self,
        credential: PersistentCredential,
    ) -> PersistentCredentialStrategyResult:
        ...
```

Strategy result is a closed typed union:

```text
PersistentStrategyResolved(identity, renewal)
PersistentStrategyNotApplicable
PersistentStrategyRejected(reason, disposition)
```

`NOT_APPLICABLE` means “this strategy does not own this format; try the next registered strategy.” It is not represented by `None` or `False`.

The ordered resolver:

```python
class PersistentCredentialResolver(Protocol):
    async def resolve(
        self,
        credential: PersistentCredential,
    ) -> PersistentCredentialResolution:
        ...
```

Resolution result:

```text
PersistentCredentialResolved(identity, renewal)
PersistentCredentialRejected(reason, disposition)
```

If all strategies return `NOT_APPLICABLE`, the resolver returns an explicit `UNSUPPORTED` rejection.

A strategy that recognizes its format but finds it invalid returns a terminal rejection; later strategies are not tried. The legacy strategy is a fallback for unprefixed 4.2.0 credentials and should be ordered after any future explicitly-prefixed formats.

## Legacy auth-token strategy

The compatibility adapter `LegacyAuthTokenStrategy` owns only the 4.2.0 deterministic format.

It is the terminal fallback for unprefixed credentials and expects the source-backed shape:

```text
15 hex chars + one-or-more decimal contact-id digits + 15 hex chars
```

Its parser therefore has only explicit success/failure variants:

```text
LegacyTokenParsed
LegacyTokenMalformed
```

`PersistentStrategyNotApplicable` is used by other format strategies (for example a future `opaque_v2` prefix strategy). When the legacy fallback is configured last, any remaining malformed unprefixed credential terminates as `MALFORMED` rather than leaking through as an implicit miss.

The strategy then:

1. parses the contact id;
2. loads the contact through `AuthSubjectStore`;
3. maps missing/disabled subjects to persistent-credential rejection;
4. computes the expected legacy credential through the existing injected `CredentialVersionTokenFactory`;
5. compares supplied and expected values with constant-time comparison;
6. on success returns the resolved identity and a refresh directive carrying the same credential with a 30-day lifetime;
7. on invalid/stale input returns a clear directive.

The MD5 formula remains in the existing Webasyst compatibility token factory; persistent-login application code contains no MD5 implementation.

## Issuance is separate from authentication

Persistent login is not a field on `BackendPasswordCredentials`.

Do not add:

```python
remember: bool
```

or any nullable equivalent.

Password authentication continues to produce an authenticated subject/session only.

If the caller wants a long-lived credential after successful authentication, it explicitly invokes:

```text
IssuePersistentCredential
```

This use case takes an authenticated subject, reloads the current auth identity through `AuthSubjectStore`, and delegates to the configured issuer.

Issuer port:

```python
class PersistentCredentialIssuer(Protocol):
    async def issue(
        self,
        identity: AuthIdentity,
    ) -> PersistentCredentialIssueResult:
        ...
```

The initial issuer is `LegacyAuthTokenIssuer`, backed by the existing credential-version token factory.

Issue result is explicit:

```text
PersistentCredentialIssued(credential, lifetime)
PersistentCredentialIssueRejected(reason)
```

No call means “do not issue/replace a persistent credential.” That is different from revoking an existing credential and matches 4.2.0 behavior where ordinary `remember=false` does not generally clear an existing `auth_token`.

## Shared backend-session establishment

Password login and persistent restore need the same session creation semantics:

- create `SessionStateStore` state;
- register `AuthSessionKey` in `AuthSessionRegistry`;
- use the current credential-version token for session invalidation;
- compensate by revoking freshly created state if active-auth registry registration raises an infrastructure error.

This orchestration must not be duplicated.

Introduce an application-owned `BackendSessionEstablisher` service used by both `AuthenticateBackendPassword` and persistent restore.

Input:

```text
AuthIdentity + SessionMetadata
```

Result:

```text
BackendSessionEstablished(subject, session_key)
BackendSessionEstablishmentRejected(reason)
```

Infrastructure faults still propagate as exceptions.

`AuthenticateBackendPassword` maps this result to its existing `AuthenticationResult`; persistent restore maps it to its persistent-login result.

## Restore use case

Application operation:

```text
RestoreBackendSessionFromPersistentCredential
```

Input:

```text
PersistentCredential + SessionMetadata
```

Flow:

```text
PersistentCredential
    -> PersistentCredentialResolver
    -> PersistentCredentialResolved(identity, renewal)
    -> BackendSessionEstablisher
    -> PersistentLoginRestored
```

Expected rejection never uses exceptions or sentinel absence.

Result:

```text
PersistentLoginRestored(
    subject,
    session_key,
    credential_disposition=RefreshCredential(...),
)

PersistentLoginRejected(
    reason,
    credential_disposition=ClearCredential | KeepCredential,
)
```

## Credential transport disposition

Application code does not set cookies. It returns transport-neutral intent.

Closed disposition union:

```text
RefreshPersistentCredential(credential, lifetime)
ClearPersistentCredential
KeepPersistentCredential
```

Mapping for the initial legacy strategy:

- successful restore -> `RefreshPersistentCredential` with the same value and 30-day lifetime;
- malformed/unsupported/invalid/stale/missing-subject/disabled-subject credential -> `ClearPersistentCredential`;
- temporary inability to establish a new session -> `KeepPersistentCredential` so a valid long-lived credential is not destroyed because transient session infrastructure failed.

Presentation later maps these directives to `Set-Cookie` / cookie deletion.

Cookie name/domain/path/`Secure`/`SameSite` are presentation/deployment policy and do not enter application contracts.

When remember-me is globally disabled, the presentation/composition path does not invoke persistent restore at all; an existing credential is left unchanged, matching 4.2.0.

The legacy cookie name remains `auth_token` in the future Webasyst presentation adapter. Legacy `HttpOnly=true` behavior must be preserved. `Secure=false` from the old PHP call is not adopted as a core invariant; deployment may require secure cookies.

## Remember UI preference is not authentication state

Legacy `remember` and `auth_token` cookies have different purposes:

- `auth_token` is the long-lived authentication credential;
- `remember` is a UI preference used to pre-check the remember-me control.

The `remember` preference does not belong in persistent-login application/domain contracts.

A future presentation adapter may preserve the legacy UI cookie separately.

## Configuration

Initial composition:

```text
accepted persistent strategies:
  1. legacy_auth_token

issuer:
  legacy_auth_token
```

Future migration can become:

```text
accepted persistent strategies:
  1. opaque_v2
  2. legacy_auth_token

issuer:
  opaque_v2
```

No persistent-login use case changes are required for that migration.

The registry ordering is explicit configuration. Strategies are not discovered through globals or dynamic imports.

## Security properties

- never log raw persistent credentials;
- legacy credential comparison uses constant-time comparison;
- malformed legacy credentials are rejected before contact lookup; explicitly-prefixed formats get their own strategy first;
- missing/disabled/invalid credentials are ordinary typed negative outcomes;
- database/I/O failures remain exceptional;
- public HTTP adapters should coarsen rejection detail where disclosure could aid enumeration;
- successful restore always creates a new normal session rather than treating the persistent credential itself as a session id;
- legacy deterministic token issuance is compatibility-only and can later be replaced without changing application flows.

## No persistence schema change in this slice

Legacy `auth_token` is stateless. The slice introduces no table for persistent credentials.

Existing tables/components reused:

- `wa_contact` through `AuthSubjectStore`;
- `wa_contact_auths` through `AuthSessionRegistry`;
- Python `SessionStateStore`;
- `CredentialVersionTokenFactory`.

A future opaque-token issuer/resolver may introduce a dedicated store and migration as a separate slice.

## Proposed package additions

```text
src/gomazon_webasyst/
  application/
    persistent_login.py
    persistent_values.py
    session_establishment.py
    ports/
      persistent_credentials.py
  contracts/
    persistent_login.py
  infrastructure/
    auth/
      persistent_credentials.py
  compatibility/webasyst/auth/
    persistent.py
  composition/
    auth.py                  # extend wiring only
```

Exact file boundaries may be adjusted during implementation as long as dependency direction and contracts above remain unchanged.

## Error/result domains

Persistent credential resolution reasons are a closed `EnumStr` domain, initially covering:

```text
MALFORMED
UNSUPPORTED
INVALID
SUBJECT_NOT_FOUND
SUBJECT_DISABLED
```

Persistent issue rejection reasons initially cover:

```text
SUBJECT_NOT_FOUND
SUBJECT_DISABLED
```

Issuer storage/I/O failures are infrastructure exceptions, not ordinary issue-result variants.

Persistent restore rejection reasons initially cover:

```text
CREDENTIAL_REJECTED
SESSION_UNAVAILABLE
```

Detailed internal resolution reasons may be coarsened by the restore/application or presentation boundary to avoid leaking account state.

No reason is represented as `None`, bool, empty string or magic value.

## Characterization and tests

### Source-backed characterization

Tests must name the relevant 4.2.0 methods and verify:

- `waAuth::getToken()` exact format/formula;
- `_remember()` 30-day `auth_token` issuance when remember is requested/enabled;
- `_remember()` does not generally clear `auth_token` merely because ordinary password login used `remember=false`;
- `_authByCookie()` extracts contact id from between 15-char prefix/suffix;
- successful cookie auth refreshes expiry using the same token value;
- invalid/stale cookie auth clears the credential;
- `clearAuth()` clears `auth_token`;
- `remember` is a separate UI cookie.

### Unit tests

Cover:

- frozen/hashable persistent VOs;
- legacy token shape parser typed outcomes;
- ordered resolver strategy semantics (`resolved`, `not applicable`, terminal reject, unsupported);
- extension with a fake `opaque_v2` strategy without modifying use cases;
- legacy issuer exact credential and 30-day lifetime;
- functional legacy verification while the adapter implementation uses constant-time comparison;
- issue use case subject missing/disabled/success;
- shared session establisher compensation behavior;
- restore invalid -> clear;
- restore success -> new session + refresh;
- session-establishment failure -> keep;
- no `Optional`/bool sentinel contracts.

### Integration tests

Using SQLite-backed legacy contacts + active-auth registry:

1. seed a backend user;
2. issue a legacy persistent credential;
3. restore a fresh session from it;
4. verify a new `AuthSessionKey` is registered;
5. mutate password/login data;
6. verify old persistent credential becomes rejected + clear directive;
7. logout/session revocation remains independent of the persistent credential transport directive; a future Webasyst HTTP logout adapter clears `auth_token` as transport behavior because legacy credentials have no server-side revocation record.

### Architecture tests

Extend guards to ensure:

- application persistent-login code imports no `hashlib`, SQLAlchemy, FastAPI/Starlette or cookie types;
- operation/lookup contracts do not use `Optional` sentinel semantics;
- legacy token format classes are not imported by application code;
- adding a second strategy does not require a new resolver method or branch in restore use case.

## Explicit non-goals

Do not in this slice:

- redesign password hashing;
- add token rotation/storage for opaque tokens;
- create login/logout HTTP routes;
- implement cookie domain/path handling;
- copy legacy insecure cookie flags into application policy;
- merge remember preference with authentication credential state;
- implement permissions or OAuth.

## Acceptance criteria

The slice is ready for implementation when:

- legacy source behavior above is captured in tests;
- persistent credential acceptance is strategy-based;
- issuance is separate from password authentication;
- restore creates a standard backend session through shared session-establishment orchestration;
- all ordinary outcomes are explicit typed variants;
- no new persistence schema is required;
- composition can later accept legacy and opaque formats simultaneously while issuing only the configured format;
- `AGENTS.md` records the compatibility-bridge and persistence-separation decisions.
