# Webasyst Backend Password Auth & Session Foundation — Design Specification

Status: accepted design baseline
Date: 2026-09-14
Repository: `boltholds/gomazon-webasyst`

## Goal

Implement the first authentication vertical slice for Webasyst 4.2.0: backend password authentication plus authenticated-session resolution/revocation, while keeping identity lookup extensible and representing expected negative outcomes as explicit typed results.

This slice deliberately excludes remember-me cookies, frontend signup/confirmation, one-time passwords, groups/permissions, OAuth/social/Webasyst ID, and API OAuth2 tokens.

## Sources of truth

Compatibility behavior is derived from the supplied Webasyst Framework 4.2.0 source, with official Webasyst documentation as a secondary reference. Per ADR-015, the supplied 4.2.0 source wins when current documentation differs.

Relevant source:

- `wa-system/auth/waAuth.class.php`
- `wa-system/config/waAuthConfig.class.php`
- `wa-system/config/waBackendAuthConfig.class.php`
- `wa-system/contact/waContact.class.php`
- `wa-system/user/waAuthUser.class.php`
- `wa-system/webasyst/lib/models/waContactAuths.model.php`
- legacy table definitions for `wa_contact`, `wa_contact_emails`, `wa_contact_data`, and `wa_contact_auths`

Observed 4.2.0 behavior important to this slice:

- backend auth requires `is_user = 1`;
- password-backed lookup ignores contacts with an empty password;
- enabled login fields are configuration-driven and ordered;
- valid email/phone shapes get priority, but lookup may continue through other configured fields if the preferred field does not find a contact;
- email lookup uses the primary email (`sort = 0`) and first contact by id;
- phone lookup uses primary phone data (`sort = 0`), normalized phone values, and configured phone transformation fallback;
- contact login lookup uses `wa_contact.login`;
- legacy password verification delegates to `waContact::verifyPasswordHash()`; default hashing is MD5, but installations may override `wa_password_hash()` / `wa_password_verify()`;
- session state (`auth_user`) is stored in PHP session storage;
- `wa_contact_auths` is a separate active-auth registry/revocation table keyed by `(contact_id, session_id)` and is not the session state store itself;
- the legacy credential token derives from contact `create_datetime + login + password_hash` and is used to detect credential changes;
- `waAuthUser` periodically checks credential-token mismatch, banned/deleted state, and whether the active-auth registry row still exists.

## Cross-project invariants

This design introduces two project-wide ADRs in `AGENTS.md`.

### Explicit expected outcomes

Expected negative outcomes are values, not sentinels:

```text
normal operation
  -> SuccessVariant | ErrorVariant
```

Do not use `None`, `False`, empty values, or exceptions to encode an ordinary lookup miss, rejected credentials, revoked session, or similar expected branch.

Infrastructure failures stay exceptional. A database outage must never be converted into `IDENTITY_NOT_FOUND`.

### Policy-driven extensibility

Extensible lookup/selection is policy + registry driven:

```text
raw input
  -> policies
  -> typed plan
  -> directory/registry
  -> typed result
```

Do not create central interfaces with `find_by_login`, `find_by_email`, `find_by_phone`, and future `find_by_*` methods.

## Auth slice boundaries

The first auth slice is:

```text
Backend password authentication
Authenticated session creation
Authenticated session resolution
Authenticated session revocation/logout
```

Out of scope:

- remember-me / `auth_token` cookie;
- frontend auth confirmation and signup policies;
- one-time-password mode;
- recovery/reset flows;
- groups, roles and app permissions;
- OAuth/social login and Webasyst ID;
- API OAuth2 access tokens/auth codes;
- PHP session-file interoperability;
- password rehash/migration on successful login.

## Identity contracts

An identity is the auth-facing projection required for password/session decisions. It is not an ORM row and does not expose arbitrary contact fields.

Conceptually:

```python
class AuthIdentity(BaseModel):
    id: int
    login: str
    password_hash: str
    is_user: int
    create_datetime: datetime
```

If a policy/resolver needs source-specific metadata (for example a normalized primary phone), that metadata remains inside the lookup adapter or a source-specific result; it is not added as nullable fields to every identity.

## Open identity keys

The lookup key is an extension point:

```python
class IdentityKey(BaseModel):
    scheme: str
    value: str
```

`scheme` intentionally is not a closed `EnumStr`: later installations may register `employee_id`, external SSO identifiers, marketplace-specific identities, or other schemes without changing the auth-core contract.

Built-in compatibility schemes initially include `login`, `email`, and `phone` as registered implementations, not as methods on the directory port.

## Login policies

Policies convert a raw backend identifier plus auth configuration into an ordered lookup plan.

```text
BackendLoginInput
  -> LoginPolicySet
  -> IdentityLookupPlan(keys in order)
```

The policy set owns recognition/ordering semantics; the directory owns data lookup.

This separation matters because Webasyst 4.2.0 prioritizes a syntactically valid email or phone but can still continue through other configured login fields if the preferred lookup misses.

A policy API is conceptually:

```python
class LoginPolicy(Protocol):
    def evaluate(self, value: str, context: LoginPolicyContext) -> LoginPolicyDecision: ...
```

Decisions are closed variants such as:

```text
PolicyContribute(keys)
PolicySkip
PolicyReject(error)
```

`LoginPolicySet` merges contributions into one ordered, deduplicated `IdentityLookupPlan` according to configuration. Adding a new login mechanism registers another policy; it does not add another branch to `AuthenticateBackendPassword`.

## Identity directory

The application-facing port has one resolution operation:

```python
class IdentityDirectory(Protocol):
    async def resolve(self, plan: IdentityLookupPlan) -> IdentityResolution: ...
```

The concrete Webasyst directory owns a resolver registry keyed by `IdentityKey.scheme`:

```text
"login" -> legacy contact-login resolver
"email" -> legacy primary-email resolver
"phone" -> legacy primary-phone resolver
```

A resolver can be added without changing the port or auth use case.

The directory evaluates keys in plan order and returns the first compatible identity according to the registered resolver semantics, matching the legacy `lookupByLoginFields(..., 'first')` behavior.

## Identity resolution results

Expected outcomes are explicit:

```text
IdentityResolution
  = IdentityResolved(identity, matched_key)
  | IdentityResolutionError(type)
```

Initial error domain may include:

```text
NOT_FOUND
REJECTED_BY_POLICY
UNSUPPORTED_SCHEME
```

Banned/non-user contacts are not exposed to the public login response as a distinguishable account-enumeration signal. Adapters/use cases may retain richer internal reason codes, but presentation maps security-sensitive credential failures to a coarse external invalid-credentials response.

Ambiguity is not introduced as a Webasyst-compatibility error in this slice because the 4.2.0 SQL explicitly takes the first matching contact by id for email/phone lookups.

## Password verification

Application code depends on a verifier port:

```python
class PasswordVerifier(Protocol):
    def verify(self, candidate: SecretStr, stored_hash: str) -> PasswordVerification: ...
```

Expected result:

```text
PasswordVerification
  = PasswordAccepted
  | PasswordVerificationError(type)
```

Initial error types:

```text
INVALID
UNSUPPORTED_SCHEME
```

The legacy adapter reproduces `waContact::verifyPasswordHash()` compatibility. The default Webasyst 4.2.0 behavior compares `md5(candidate)` to the stored hash, but the adapter boundary must allow an installation-specific verifier equivalent to `wa_password_verify()`.

This slice MUST NOT write new MD5 password hashes or automatically rehash successful logins. Password migration is a separate security/migration decision because the PHP application may still coexist with the Python rewrite.

## Authentication use case

The main operation is:

```text
AuthenticateBackendPassword
  -> LoginPolicySet.plan
  -> IdentityDirectory.resolve
  -> PasswordVerifier.verify
  -> backend eligibility policy
  -> SessionStateStore.create
  -> AuthSessionRegistry.register
  -> AuthenticationResult
```

The final result is also explicit:

```text
AuthenticationResult
  = AuthenticationSucceeded(subject, session)
  | AuthenticationRejected(type)
```

Presentation MUST be able to map multiple internal rejection reasons to one external invalid-credentials response so login endpoints do not disclose whether an account exists.

No `bool`, `None`, or exception is used for normal credential rejection.

## Session model: state store vs active-auth registry

Legacy Webasyst has two separate responsibilities and Python keeps them separate.

### SessionStateStore

Stores the authenticated session state analogous to legacy `auth_user` in PHP session storage.

Conceptual port:

```python
class SessionStateStore(Protocol):
    async def create(self, subject: AuthenticatedSubject, metadata: SessionMetadata) -> SessionCreationResult: ...
    async def resolve(self, session_id: str) -> SessionStateResolution: ...
    async def revoke(self, session_id: str) -> SessionRevocationResult: ...
```

The storage adapter is DI-selected. A later Redis, database, or PHP-session compatibility adapter must be introducible without changing auth use cases.

### AuthSessionRegistry

Maps the active authorization to legacy `wa_contact_auths` semantics:

```python
class AuthSessionRegistry(Protocol):
    async def register(self, record: AuthSessionRegistration) -> RegistryWriteResult: ...
    async def check(self, contact_id: int, session_id: str) -> RegistryCheckResult: ...
    async def touch(self, contact_id: int, session_id: str) -> RegistryTouchResult: ...
    async def revoke(self, contact_id: int, session_id: str) -> RegistryRevocationResult: ...
```

The first SQLAlchemy adapter maps the existing `wa_contact_auths` table; it does not create a replacement table.

The registry is not treated as the session-state store.

## Credential-version token

Legacy Webasyst derives a deterministic token from:

```text
md5(create_datetime + login + password_hash)
```

and embeds the contact id between the first/last 15 hash characters.

Python represents this through an injected `CredentialVersionTokenFactory`. The value is a compatibility/version marker, not a modern bearer credential.

Session state stores the version token captured at authentication. Session resolution can compare it with the current identity token and return an explicit `CREDENTIALS_CHANGED` result.

## Session resolution

Conceptual flow:

```text
ResolveBackendSession(session_id)
  -> SessionStateStore.resolve
  -> IdentityDirectory/read-by-subject-id capability
  -> CredentialVersionTokenFactory
  -> AuthSessionRegistry.check
  -> backend eligibility check
  -> optional registry touch
  -> SessionResolutionResult
```

Expected result family:

```text
SessionResolutionResult
  = SessionResolved(subject, session)
  | SessionResolutionError(type)
```

Initial error domain:

```text
NOT_FOUND
EXPIRED
REVOKED
CREDENTIALS_CHANGED
SUBJECT_UNAVAILABLE
SUBJECT_DISABLED
```

The exact timeout/touch policy is configuration, not hard-coded into the application use case.

Legacy Webasyst checks credential changes, ban/deletion, and active-registry revocation periodically rather than on every request. The first Python compatibility policy must make that cadence explicit and testable; strict-every-request mode may be selected by configuration.

## Read-by-subject-id without `find_by_*`

Session resolution needs identity loading by stable subject id. This is not another login scheme and therefore does not belong in the login policy registry.

Use a subject-oriented port/capability such as:

```python
class AuthSubjectStore(Protocol):
    async def get(self, subject_id: int) -> SubjectResolution: ...
```

`SubjectResolution` is explicit (`SubjectResolved | SubjectResolutionError`), not `AuthIdentity | None`.

This keeps login-key lookup extensible while keeping stable identity retrieval explicit and intent-oriented.

## Logout/revocation

`LogoutBackendSession` coordinates both stores:

```text
session id
  -> SessionStateStore.revoke
  -> AuthSessionRegistry.revoke
  -> LogoutResult
```

The operation is idempotent at the application boundary. Already-missing state is represented by an explicit successful/idempotent outcome, not an exception.

Remember-me cookie deletion is outside this slice because remember-me itself is outside this slice.

## Error and security model

Three categories are distinct:

1. **Expected negative outcomes** — discriminated result variants.
2. **Security-coarsened external responses** — presentation may merge internal reasons to prevent enumeration.
3. **Infrastructure/programming failures** — typed exceptions/errors that are not converted into ordinary negative results.

A database timeout must never be returned as `NOT_FOUND`. A malformed policy registration is a configuration/programming error, not `INVALID_CREDENTIALS`.

## Persistence mapping

The first compatibility adapter reads existing Webasyst tables:

```text
wa_contact
wa_contact_emails
wa_contact_data          # phone
wa_contact_auths
```

No destructive schema migration is part of this slice.

Existing contact/auth columns remain infrastructure-private. Pydantic auth contracts cross the persistence boundary.

## Composition

The composition root wires:

```text
LoginPolicySet
IdentityDirectory + resolver registry
AuthSubjectStore
PasswordVerifier
CredentialVersionTokenFactory
SessionStateStore
AuthSessionRegistry
AuthenticateBackendPassword
ResolveBackendSession
LogoutBackendSession
```

No global auth singleton or service locator is introduced.

## Testing strategy

### Contract tests

Prove explicit success/error unions and ensure ordinary negative results cannot be represented by `None`/bool sentinels.

### Policy tests

Characterize Webasyst login priority, configured field ordering, email/phone recognition, and extension by registering a new policy without changing auth use cases.

### Directory tests

Use a fake resolver registry to prove scheme extensibility and ordered first-success resolution. Legacy SQLAlchemy resolver tests cover login/email/phone behavior against representative legacy rows.

### Password tests

Characterize default MD5 verification and an injected custom verifier. Prove the application layer does not know the hashing algorithm.

### Session tests

Test state-store outcomes independently from `wa_contact_auths` registry outcomes. Cover create, resolve, credentials-changed, revoked, disabled/unavailable subject, touch, and idempotent logout.

### Architecture tests

Prevent SQLAlchemy, FastAPI, cookie/session framework types, and concrete password algorithms from entering application/contracts.

### Integration tests

Exercise password login -> session creation -> session resolution -> logout using the composition root and a concrete test session-state adapter plus SQLAlchemy legacy-table adapters.

## Completion criteria

The slice is complete when:

- no normal auth lookup/rejection/session miss uses `None`, `False`, or bool as a result contract;
- identity lookup is policy/registry driven and adding a scheme does not add `find_by_*` methods;
- legacy login ordering and source behavior are characterized;
- password verification is an injected adapter and application code contains no MD5 logic;
- session state and `wa_contact_auths` registry are separate ports;
- credential-version invalidation is explicit;
- backend eligibility and security response coarsening are tested;
- existing legacy tables are used without destructive migration;
- architecture, unit, persistence-contract, and integration tests pass;
- `AGENTS.md` records the project-wide typed-negative-result and policy/registry ADRs.
