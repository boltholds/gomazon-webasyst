# Backend Session HTTP Bridge Design

Status: proposed for written-spec review
Date: 2026-09-19

## 1. Purpose

The Python rewrite already has a complete backend authentication/session core:

- `AuthenticateBackendPassword`;
- `ResolveBackendSession`;
- `LogoutBackendSession`;
- persistent credential issue/restore/revoke;
- replaceable `SessionStateStore`;
- active-session registry and credential-change validation.

What is still missing is the HTTP boundary that turns browser credentials into those use cases and turns their typed outcomes back into cookie operations.

This bridge is a prerequisite for Webasyst-compatible `/api.php/auth`. The OAuth authorization action needs a trustworthy current backend subject, but OAuth code MUST NOT read session cookies, `auth_token`, session storage or SQL directly.

The bridge therefore has one responsibility:

```text
browser credential state
        ↓
typed session/persistent credential input
        ↓
existing auth use cases
        ↓
typed current-subject/login/logout result
        ↓
credential dispositions
        ↓
HTTP cookie adapter
```

It is not a second authentication system.

## 2. Scope

This slice includes:

- current backend subject resolution from a Python session credential;
- persistent-login fallback through the existing persistent credential use case;
- password-login orchestration over `AuthenticateBackendPassword`;
- explicit remember intent without putting a remember flag into password credentials;
- logout orchestration;
- transport-neutral session credential dispositions;
- Webasyst `auth_token` cookie extraction/application;
- a Python-native backend session cookie;
- configurable cookie names/security policy in composition;
- User-Agent -> `SessionMetadata` normalization;
- reusable HTTP bridge helpers/components for the later OAuth authorization router;
- focused compatibility, unit, architecture and ASGI tests.

This slice does not include:

- `/api.php/auth` consent/redirect logic;
- OAuth CSRF/consent forms;
- `/api.php/token`, `/api.php/revoke` or token-headless;
- PHP session-file or `PHPSESSID` interoperability;
- recreation of PHP `$_SESSION`;
- Webasyst ID/social OAuth login;
- a new auth database/schema;
- Redis/Supabase session adapters;
- the legacy `remember` UI-preference cookie;
- a standalone production login page.

## 3. Source-of-truth and compatibility rules

The supplied Webasyst Framework 4.2.0 source remains authoritative for legacy persistent-login behavior.

Existing ADR-024 and ADR-025 remain unchanged:

- persistent credentials are opaque application values;
- the legacy deterministic `auth_token` format stays compatibility-only;
- password authentication establishes a normal backend session first;
- persistent credential issuance is a separate operation;
- `remember` is not added to `BackendPasswordCredentials`;
- session-only login does not clear an existing `auth_token`;
- if persistent login is globally disabled, persistent restore is not invoked and an existing `auth_token` is left untouched;
- logout clears persistent credential transport.

## 4. Architecture taxonomy: Entity / VO / Services / Composite

All new backend-session bridge application code MUST be classifiable as Entity, VO, Service, or Composite.

The taxonomy is a responsibility taxonomy inside the existing architecture. It does not replace ports, infrastructure, compatibility, presentation or composition.

### 4.1 Entity

This slice introduces no new domain Entity.

That is intentional. The identity-bearing objects already exist:

- `AuthenticatedSubject`;
- `AuthSessionKey`;
- `StoredAuthSession`.

Creating a new wrapper Entity solely to satisfy a folder layout would duplicate identity and is prohibited.

If implementation later discovers a genuinely identity-bearing bridge object, the design must be amended before adding it.

### 4.2 Value Objects

New immutable values/state variants include:

- `RememberIntent` — closed `EnumStr`: `SESSION_ONLY | PERSIST`;
- `SessionCredentialProvided(session_id)`;
- `SessionCredentialMissing`;
- `SessionCredentialMalformed`;
- `PersistentCredentialProvided(credential)`;
- `PersistentCredentialMissing`;
- `IssueSessionCredential(session_id)`;
- `ClearSessionCredential`;
- `KeepSessionCredential`;
- explicit current-subject/login rejection reasons as closed `EnumStr` domains;
- compatibility HTTP cookie-name/policy VOs.

No operation result is represented by `None`, an empty string, `False`, or a nullable state bag.

### 4.3 Services

The bridge reuses existing auth use cases as injected Services:

- `AuthenticateBackendPassword`;
- `ResolveBackendSession`;
- `LogoutBackendSession`;
- `IssuePersistentCredential`;
- `RestoreBackendSessionFromPersistentCredential`;
- `RevokePersistentCredential`.

New Services are added only when a single coherent rule exists. Examples:

- HTTP credential extraction service;
- HTTP cookie mutation service;
- request metadata normalization service.

No service may own the complete login/session/persistent orchestration.

### 4.4 Composites

Three Composites own sequencing:

- `BackendCurrentSubjectFlow`;
- `BackendPasswordLoginFlow`;
- `BackendLogoutFlow`.

A Composite may sequence Services and translate their typed results into bridge-specific dispositions. It MUST NOT:

- query SQL;
- access FastAPI/Starlette requests;
- write cookies;
- inspect ORM rows;
- understand the legacy `auth_token` token formula;
- create its own session store;
- hide service lookup through a locator.

## 5. Application package shape

Target application structure:

```text
application/
  backend_session_bridge/
    __init__.py
    vo/
      __init__.py
      credentials.py
      remember.py
      results.py
    services/
      __init__.py
    composites/
      __init__.py
      current_subject.py
      login.py
      logout.py
```

There is deliberately no `entities/` package until the slice owns a real Entity.

Application-owned ports remain under `application/ports/`; HTTP-specific types remain outside application.

## 6. Session credential model

The Python backend session credential is the existing opaque `SessionId`.

The HTTP layer transports it in a dedicated Python-native cookie.

Default cookie name:

```text
gomazon_session
```

This cookie is NOT named `PHPSESSID` and does not claim PHP session interoperability.

The cookie value is exactly `SessionId.value`.

The runtime `SessionStateStore` remains authoritative for expiry/revocation. The cookie itself is a browser-session cookie and carries no application-level session TTL.

### 6.1 Input normalization

HTTP extraction normalizes raw cookie state to exactly one variant:

```text
SessionCredentialMissing
SessionCredentialMalformed
SessionCredentialProvided(SessionId)
```

An empty Python session cookie is malformed and should be cleared.

Any non-empty opaque value is representable as `SessionId`; resolution determines whether it exists, expired, revoked or invalidated.

## 7. Persistent credential transport

The default persistent cookie name remains the legacy:

```text
auth_token
```

Its content is wrapped in the existing `PersistentCredential`.

The HTTP bridge does not know the credential format.

For Webasyst compatibility, PHP-falsy persistent cookie values such as empty string and string `"0"` are treated as no usable credential and are not sent into restore. This matches the legacy `!empty($_COOKIE['auth_token'])` gate.

A normal non-empty persistent value is:

```text
PersistentCredentialProvided(PersistentCredential(...))
```

No parser for the legacy hash/contact-id shape exists in HTTP code. Format acceptance remains in the registered persistent credential strategy.

## 8. Session credential dispositions

Application Composites never set cookies directly.

They return one explicit session transport intent:

```text
IssueSessionCredential(SessionId)
ClearSessionCredential
KeepSessionCredential
```

Meaning:

- `Issue`: presentation must set/replace the Python session cookie;
- `Clear`: presentation must expire the Python session cookie;
- `Keep`: presentation makes no session-cookie mutation.

Persistent credential intent reuses the existing:

```text
RefreshPersistentCredential
ClearPersistentCredential
KeepPersistentCredential
```

This preserves the split established by ADR-025.

## 9. Current backend subject Composite

`BackendCurrentSubjectFlow` is the canonical entry point future browser-authenticated surfaces use, including `/api.php/auth`.

Input:

```text
BackendCurrentSubjectRequest
  session_credential: SessionCredentialInput
  persistent_credential: PersistentCredentialInput
  session_metadata: SessionMetadata
  persistent_login_mode: enabled | disabled
```

`persistent_login_mode` is represented by a closed typed setting/decision, not nullable state.

### 9.1 Resolution order

The flow is strictly:

```text
provided Python session?
  ├─ yes -> ResolveBackendSession
  │          ├─ resolved -> current subject
  │          └─ rejected -> mark session for clearing
  │
  └─ no/malformed -> no resolved subject

resolved subject?
  ├─ yes -> stop
  └─ no
      ↓
persistent login enabled?
  ├─ no -> stop; DO NOT inspect/clear auth_token
  └─ yes
      ↓
usable persistent credential?
  ├─ no -> unauthenticated
  └─ yes -> RestoreBackendSessionFromPersistentCredential
```

A valid session always wins over a persistent cookie. Persistent restore is a fallback, not a parallel identity source.

### 9.2 Valid session

When `ResolveBackendSession` returns `SessionResolved`:

- return the same `AuthenticatedSubject`;
- return `KeepSessionCredential`;
- return `KeepPersistentCredential`;
- do not invoke persistent restore.

### 9.3 Invalid/stale session with no successful fallback

A provided session cookie that fails resolution results in `ClearSessionCredential`.

The internal session resolution reason may be retained in a typed bridge rejection/diagnostic value but must not be exposed as sensitive public detail by default.

### 9.4 Persistent restore success

When persistent restore succeeds:

- return the restored subject;
- return `IssueSessionCredential(restored.session_key.session_id)`;
- return the persistent credential disposition from the existing restore result verbatim.

For legacy `auth_token`, successful restore normally produces `RefreshPersistentCredential` for the same value and lifetime.

### 9.5 Persistent restore rejection

When restore rejects:

- no current subject is returned;
- stale Python session credential remains scheduled for clearing if one was provided and rejected;
- persistent disposition is preserved exactly:
  - clear when credential is invalid/stale/malformed under the registered strategy;
  - keep when a valid credential could not establish runtime session state.

Infrastructure faults remain exceptional and are not mapped to unauthenticated.

## 10. Password login Composite

`BackendPasswordLoginFlow` receives:

```text
BackendPasswordLoginRequest
  credentials: BackendPasswordCredentials
  remember_intent: RememberIntent
  persistent_login_mode
```

It calls `AuthenticateBackendPassword` first.

### 10.1 Authentication rejection

If primary authentication rejects:

- return typed login rejection;
- `KeepSessionCredential`;
- `KeepPersistentCredential`;
- do not issue persistent credentials.

### 10.2 Authentication success

If authentication succeeds:

- return authenticated subject;
- return `IssueSessionCredential(authentication.session_key.session_id)`.

### 10.3 Session-only intent

For `RememberIntent.SESSION_ONLY`:

- do not call `IssuePersistentCredential`;
- return `KeepPersistentCredential`.

This intentionally preserves an existing `auth_token`, matching Webasyst 4.2.0 behavior.

### 10.4 Persistent intent

For `RememberIntent.PERSIST` while persistent login is enabled:

- call `IssuePersistentCredential(subject)`;
- issued -> translate to `RefreshPersistentCredential(credential, lifetime)`;
- issue rejection -> login still succeeds, persistent transport stays unchanged.

Primary login success is not rolled back solely because persistent issuance failed.

The result includes a closed persistence outcome so callers may report that remember-me was unavailable without treating authentication as failed.

### 10.5 Persistent login disabled

When globally disabled:

- persistent issuance is not invoked regardless of remember intent;
- existing `auth_token` remains untouched.

## 11. Logout Composite

`BackendLogoutFlow` receives the normalized session credential state.

Behavior is idempotent:

- provided valid/non-empty session id -> invoke `LogoutBackendSession`;
- missing/malformed session credential -> no session lookup is required;
- always return `ClearSessionCredential`;
- always invoke `RevokePersistentCredential` and return its `ClearPersistentCredential` intent.

Thus logout clears browser authentication transport even if runtime session state was already absent.

Future persistent credential formats that require server-side revocation may extend the persistent credential core separately; this bridge does not invent storage semantics.

## 12. HTTP compatibility/presentation boundary

New HTTP-specific code lives outside application, for example:

```text
compatibility/webasyst/auth_http/
  vo/
  services/
  composites/

presentation/http/
  backend_session.py
```

The boundary has two directions.

### 12.1 Request normalization

It converts request data into:

- session credential input;
- persistent credential input;
- `SessionMetadata(user_agent=...)`;
- normalized remember intent when a login form is involved.

No FastAPI `Request` object crosses into application.

### 12.2 Response mutation

It converts typed dispositions into cookie operations.

No application Composite calls `set_cookie` or `delete_cookie`.

## 13. Cookie policy

Cookie policy is a composition/presentation concern.

Default policy:

### Python session cookie

- name: `gomazon_session`;
- host-only;
- path: `/`;
- `HttpOnly=true`;
- `SameSite=Lax`;
- `Secure` from explicit deployment setting;
- no `Max-Age` / `Expires` — runtime session state is authoritative.

### Persistent cookie

- name: `auth_token`;
- host-only;
- path: `/`;
- `HttpOnly=true`;
- `SameSite=Lax`;
- `Secure` from explicit deployment setting;
- `Max-Age` / `Expires` derived from `PersistentCredentialLifetime` on refresh.

Clear operations use the same name/path/security policy as set operations.

Cookie domain customization is out of scope for the first bridge. If later required, it must be modeled as explicit host-only vs explicit-domain state rather than nullable/empty domain configuration.

## 14. Settings

Composition gains explicit settings with safe defaults for development:

```text
backend_session_cookie_name = "gomazon_session"
persistent_auth_cookie_name = "auth_token"
backend_auth_cookie_secure = false
persistent_login_enabled = true
```

Cookie names are validated non-empty values.

Production deployment is expected to enable secure cookies under HTTPS.

`api_force_https` is not reused as cookie-security configuration; API transport policy and authentication-cookie policy are separate concerns.

## 15. Standalone routes

This slice does NOT mount a new standalone production login page/router in `main.py`.

The reason is deliberate: the immediate consumer is the upcoming Webasyst OAuth authorization/consent endpoint, which owns its own GET/POST/CSRF surface.

The bridge may provide presentation helper functions/classes and test-only ASGI fixtures, but no unrelated public authentication surface is added merely to prove the bridge.

This avoids introducing a cookie-changing endpoint before the OAuth slice defines its CSRF policy.

## 16. OAuth integration contract

The next OAuth authorization slice consumes only the bridge Composite:

```text
/api.php/auth Request
      ↓
HTTP bridge normalization
      ↓
BackendCurrentSubjectFlow
      ↓
CurrentBackendSubjectResolved
      ↓
OAuth authorization/consent flow
```

When the consent page accepts credentials for login, it invokes `BackendPasswordLoginFlow` and applies the returned dispositions through the same HTTP bridge.

OAuth code therefore never reads:

- `gomazon_session` directly;
- `auth_token` directly;
- session storage;
- auth session registry;
- auth subject SQL rows.

## 17. Error handling

Expected outcomes remain typed.

Current-subject resolution distinguishes at least:

- resolved;
- unauthenticated/no usable credential;
- session rejected;
- persistent credential rejected;
- persistent restore unable to establish a session.

Presentation may coarsen these to unauthenticated for public behavior.

Infrastructure failures such as database unavailable, session backend unavailable, I/O error or corruption remain exceptions and MUST NOT be translated into ordinary unauthenticated state.

## 18. Security properties

- raw passwords remain `SecretStr` inside `BackendPasswordCredentials`;
- raw passwords are never echoed in result contracts/logs;
- raw persistent credentials are never logged;
- session ids are opaque credentials and must not be logged at normal levels;
- cookie mutations always use `HttpOnly`;
- cookie security policy is explicit;
- current-subject flow never falls through from one valid resolved subject to another identity source;
- persistent restore is disabled entirely when configured off;
- password login does not silently clear or replace persistent credentials unless issuance is explicitly requested;
- no service locator/global current-user object is introduced.

## 19. Testing strategy

### 19.1 Unit tests

Pin:

- valid session wins and persistent resolver is never called;
- stale/expired/revoked session produces clear-session intent;
- missing session + valid persistent credential restores session;
- stale session + valid persistent credential restores a new session and clears/replaces stale transport;
- invalid persistent credential preserves its clear disposition;
- valid persistent credential + session-establishment failure preserves keep disposition;
- persistent-login disabled never invokes restore and never clears `auth_token`;
- session-only password login never invokes persistent issuance;
- persistent password login invokes issuance after successful auth;
- persistent issuance failure does not turn primary auth success into login failure;
- logout is idempotent and clears both transports;
- infrastructure exceptions propagate.

### 19.2 Compatibility tests

Characterize:

- legacy `auth_token` default cookie name;
- PHP-falsy `auth_token` cookie values are treated as unavailable rather than parsed;
- session-only login leaves existing persistent credential transport untouched;
- successful legacy persistent restore refreshes the same token value with its lifetime;
- logout clears `auth_token`.

### 19.3 HTTP/presentation tests

Pin:

- session cookie extraction;
- stale session cookie deletion;
- persistent refresh -> exact cookie lifetime;
- persistent clear -> expired cookie;
- keep -> no Set-Cookie for that credential;
- User-Agent metadata normalization;
- `HttpOnly`, SameSite, Secure policy;
- no cookie domain attribute in the initial host-only policy.

### 19.4 Architecture tests

Enforce:

- bridge application code contains no FastAPI/Starlette/SQLAlchemy/compatibility imports;
- no `Optional`/nullable operation states;
- no cookie names in application Composite code;
- no `PHPSESSID`/PHP session-file dependency;
- no `remember: bool` field added to `BackendPasswordCredentials`;
- no direct persistent token-format parsing in presentation;
- one resolved `SessionStateStore` instance remains shared across auth flows.

## 20. Acceptance criteria

The slice is accepted when:

1. browser credential state can be normalized without `None` sentinels;
2. current backend subject resolution prefers valid runtime session and falls back to persistent credential only when required;
3. persistent restore dispositions are preserved exactly;
4. password login remains independent from remember intent;
5. session-only login does not clear existing `auth_token`;
6. logout clears both session and persistent transport idempotently;
7. cookie writes are presentation-only;
8. the session cookie is Python-native and does not pretend to be PHP-compatible;
9. the bridge can be injected into the next `/api.php/auth` slice without OAuth code depending on auth storage/cookies;
10. full repository tests and architecture guards are green.

## 21. Explicit non-goals

Do not implement in this slice:

- OAuth consent UI;
- OAuth redirects;
- CSRF policy;
- registered OAuth clients;
- PHP session decoding;
- login HTML templates;
- Webasyst ID;
- social providers;
- persistent-token v2;
- distributed session backend;
- standalone public auth routes.

Those remain separate independently reviewable slices.
