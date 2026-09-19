# OAuth Authorization Surface Design

Status: proposed for written-spec review
Date: 2026-09-19

## 1. Purpose

The rewrite already has the three lower layers required by Webasyst 4.2.0 API OAuth:

- backend password/session/persistent authentication;
- a browser-facing backend session HTTP bridge;
- authorization-code/access-token credential use cases;
- authenticated API method execution.

What is missing is the Webasyst-compatible OAuth surface itself:

- `/api.php/auth`;
- `/api.php/token`;
- `/api.php/revoke`.

This slice completes that browser/API loop without turning transport code into another monolithic `waAPIController`.

The intended dependency direction is:

```text
legacy OAuth HTTP transport
        ↓
typed compatibility normalization
        ↓
backend session bridge + OAuth application Composites
        ↓
existing auth / ACL / API credential use cases
```

The slice preserves Webasyst 4.2.0 observable behavior where it is compatibility-relevant, while isolating insecure or obsolete legacy policy behind replaceable policies.

## 2. Scope

This slice includes:

- GET/POST `/api.php/auth`;
- backend current-subject resolution through the existing session bridge;
- OAuth-scoped backend password login for unauthenticated users;
- consent rendering;
- scope filtering by installed app + backend access;
- approve/deny/cancel behavior;
- logout from the OAuth authorization surface;
- authorization-code grants;
- implicit access-token grants;
- POST `/api.php/token`;
- `/api.php/revoke`;
- exact legacy redirect/query/fragment behavior;
- exact legacy controller-level HTTP-200 JSON/XML semantics for token/revoke;
- reuse of API enabled/HTTPS preconditions;
- minimal functional HTML for login/consent/code/error states;
- architecture, compatibility, HTTP and vertical tests.

This slice explicitly excludes:

- `/api.php/token-headless`;
- Webasyst ID;
- social login;
- registered OAuth clients;
- PKCE;
- refresh tokens;
- OpenID Connect;
- `license-cache`;
- `profile-update`;
- cron API endpoints;
- PHP session interoperability;
- a general-purpose standalone login page.

## 3. Legacy source of truth

The supplied Webasyst Framework 4.2.0 source is authoritative.

Primary files:

- `wa-system/api/waAPIController.class.php`;
- `wa-system/webasyst/lib/actions/api/webasystApiAuth.action.php`;
- `wa-system/webasyst/lib/actions/api/webasystApiToken.controller.php`;
- `wa-system/webasyst/lib/actions/api/webasystApiRevoke.controller.php`;
- `wa-system/request/waRequest.class.php`;
- backend login renderer/actions for CSRF/login form behavior.

The current Python implementation remains authoritative for already-migrated application contracts and existing ADRs.

## 4. Architectural taxonomy: Entity / VO / Services / Composite

All new OAuth application code MUST be explicitly classifiable as Entity, VO, Service, or Composite.

This taxonomy exists inside the current layer boundaries and does not replace ports, compatibility, presentation, infrastructure or composition.

### 4.1 Entity

This slice introduces one real Entity:

`OAuthConsentApplication`

Identity:

`AppId`

State:

- app id;
- display name;
- display icon reference.

It represents an installed application as shown on the consent screen.

The entity does not contain authorization logic.

No OAuth client Entity is introduced. Webasyst 4.2.0 has no registered-client store; `client_id` and `client_name` arrive directly from the request.

### 4.2 Value Objects

New immutable values include:

- `OAuthClientName`;
- `OAuthRedirectUri`;
- `OAuthRequestedScope`;
- `OAuthCsrfToken`;
- `OAuthResponseType`;
- `OAuthConsentDecision`;
- `OAuthGrantType`;
- redirect/result targets;
- revoke-target state;
- controller response-format state where required.

Existing values are reused:

- `ApiClientId`;
- `ApiScope`;
- `AppId`;
- `AuthorizationCode`;
- `ApiAccessToken`;
- `AuthenticatedSubject`.

Closed protocol/state domains use `EnumStr`.

Open identifiers remain open VOs.

No request/result state is represented by `None` or an empty-string sentinel in application code.

### 4.3 Services

Services own one rule each, for example:

- `OAuthConsentScopeService`;
- `OAuthRedirectPolicy`;
- `OAuthConsentAccessPolicy`;
- `LegacyOAuthCsrfService`;
- `LegacyOAuthRequestValidationService`;
- `LegacyOAuthControllerFormatService`;
- `LegacyOAuthCancelService`;
- `LegacyRevokeTargetExtractor`;
- HTML renderer Services.

Credential issue/exchange/revoke Services are the already-existing use cases and are injected rather than duplicated.

### 4.4 Composites

Application Composites own sequencing:

- `OAuthAuthorizationFlow`;
- `OAuthRevokeAuthenticationFlow`.

Compatibility/presentation may also use a transport Composite for normalized request state, but it MUST NOT contain hidden business rules.

No Composite may query SQL, import ORM rows, parse password hashes, write cookies directly, or dynamically load app classes.

## 5. Target package shape

```text
application/
  oauth_authorization/
    entities/
      consent_application.py
    vo/
      client.py
      authorization.py
      revoke.py
    services/
      scope.py
    composites/
      authorization.py
      revoke_authentication.py

application/ports/
  oauth_consent_apps.py
  oauth_consent_access.py
  oauth_redirect_policy.py

compatibility/webasyst/oauth/
  vo/
  services/
  composites/

presentation/http/
  legacy_oauth.py

composition/
  oauth_authorization.py
```

The package names may be shortened during implementation, but the responsibility boundaries MUST remain equivalent.

## 6. Authorization request

The authorization request is normalized from GET query parameters.

Required fields:

- `client_id`;
- `client_name`;
- `response_type`;
- `scope`.

Allowed response types:

- `code`;
- `token`.

For `response_type=token`, `redirect_uri` is also required.

For `response_type=code`, `redirect_uri` is optional.

Webasyst required-field semantics use PHP truthiness. Therefore values such as empty string and string `"0"` are invalid for required fields at the compatibility boundary.

The application flow receives an already validated typed request.

Full authorization-request validation is action-level behavior. It occurs only after a backend subject is authenticated. Outer `waAPIController` dispatch handles `cancel` and unauthenticated login before `webasystApiAuthAction::checkRequest()`. Therefore an unauthenticated request with incomplete/invalid OAuth query fields still reaches the login surface first; after successful login and redirect back to the same URL, the authenticated authorization action validates the OAuth request.

## 7. OAuth response type

`OAuthResponseType` is a closed `EnumStr`:

```text
CODE = "code"
TOKEN = "token"
```

No arbitrary response type string crosses into application orchestration.

## 8. Current backend subject

`/api.php/auth` never queries session storage or cookies directly.

It uses:

`BackendCurrentSubjectFlow`

The HTTP adapter first normalizes `gomazon_session`, `auth_token`, and User-Agent through the backend session HTTP bridge.

Any returned session/persistent credential dispositions are applied to the response through the existing cookie mutation service.

Thus a GET to the OAuth page may:

- keep an existing session;
- clear a stale session;
- restore a session through `auth_token`;
- refresh persistent transport.

OAuth code never imports the session store.

## 9. Unauthenticated authorization surface

If `BackendCurrentSubjectFlow` returns unauthenticated, the authorization endpoint renders an OAuth-scoped backend login form.

The login form:

- preserves the raw OAuth query string without requiring it to be valid yet;
- posts credentials back to the same authorization surface;
- uses `BackendPasswordLoginFlow`;
- applies the returned session/persistent credential dispositions;
- on successful login redirects to the same OAuth URL, matching the backend login action's current-URL redirect;
- on the subsequent authenticated request, full OAuth request validation begins.

The login form does not create a general public login endpoint.

`RememberIntent` remains separate from `BackendPasswordCredentials`.

## 10. CSRF

Webasyst backend login forms inject CSRF, and `webasystApiAuthAction` validates `_csrf` for authenticated POST actions.

The Python OAuth surface uses one compatibility Service:

`LegacyOAuthCsrfService`

It implements a double-submit contract:

```text
_csrf cookie == _csrf POST field
```

CSRF token generation uses secure Python entropy.

Rules:

- GET authorization/login may issue or retain the `_csrf` cookie;
- login POST validates CSRF;
- authenticated approve/deny/logout POST validates CSRF;
- the outer legacy `cancel` branch intentionally runs before CSRF validation, matching `waAPIController::dispatch()`.

Raw cookie/form CSRF values do not enter application use cases.

## 11. Cancel before authentication

Legacy `waAPIController::dispatch()` handles POST `cancel` before checking whether the user is authenticated.

This is a distinct compatibility branch and MUST NOT be merged with authenticated consent denial.

Behavior:

### response_type=token

Always redirect:

```text
redirect_uri#error=access_denied
```

The legacy code does not guard an empty redirect URI in this branch.

### response_type=code

When redirect URI exists:

```text
redirect_uri?error=access_denied
```

or:

```text
redirect_uri&error=access_denied
```

when the URI already contains `?`.

When redirect URI is absent:

- return framework error `access_denied`;
- HTTP 403;
- description references the supplied client name.

This branch does not require a current subject and does not invoke CSRF.

## 12. Consent scope

Raw requested scope is comma-separated app ids.

The application normalizes it to ordered unique `AppId` values.

Every requested app is independently filtered:

```text
present in OAuthConsentAppCatalog?
        ↓ yes
subject has backend access?
        ↓ yes
include in effective consent scope
```

Apps that are absent or unauthorized are silently omitted, matching 4.2.0.

If no app survives filtering:

- authorization surface enters typed invalid-scope state;
- legacy HTML error is `invalid_request` / `invalid scope`.

The effective scope passed to authorization-code/token issuance is exactly the surviving app ids in request order.

## 13. Consent app catalog

A new application-owned port:

`OAuthConsentAppCatalog`

resolves `AppId` to:

- `OAuthConsentApplicationResolved`;
- `OAuthConsentApplicationMissing`.

The default first implementation may be explicit/in-memory composition data until a broader app-manifest subsystem exists.

The OAuth flow does not scan directories or dynamically import application metadata.

The special legacy `webasyst` consent icon override belongs in the Webasyst compatibility catalog adapter, not in the Entity or application Composite.

## 14. Consent access policy

Consent scope authorization is intentionally separate from API method execution authorization.

A new application-owned port:

`OAuthConsentAccessPolicy`

returns a typed grant/deny decision for:

```text
AuthenticatedSubject + AppId
```

The Webasyst compatibility implementation:

- requires backend-user semantics;
- uses effective backend access;
- does NOT apply the API execution `webasyst` special-case automatically.

This preserves the source behavior in `webasystApiAuthAction`, which uses ordinary backend rights for every requested app.

## 15. Consent display

For authenticated GET after successful request/scope validation:

`OAuthAuthorizationFlow`

returns:

`OAuthConsentRequired`

containing:

- client display name;
- effective scope;
- consent application Entities.

Presentation renders minimal functional HTML.

HTML responsibilities:

- escape client name;
- escape app names;
- escape error text;
- render icons only through trusted catalog metadata;
- preserve authorization query fields in form action/hidden state;
- include CSRF field.

Application code contains no HTML.

## 16. Authenticated POST ordering

For an authenticated authorization POST, ordering is:

```text
validate authorization request
        ↓
validate CSRF
        ↓
logout?
  ├─ yes → BackendLogoutFlow → apply cookie clear → redirect back to same auth URL
  └─ no
        ↓
filter effective scope
        ↓
approve?
  ├─ yes → grant
  └─ no  → authenticated deny
```

This preserves 4.2.0 ordering: logout occurs before scope filtering; approve/deny occurs after scope filtering.

## 17. Logout inside OAuth authorization

Authenticated POST `logout`:

- requires valid CSRF;
- calls existing `BackendLogoutFlow`;
- applies both clear credential dispositions;
- redirects to the same authorization request URL;
- does not grant or deny OAuth access in that request.

The old `waLogModel` audit insertion is not recreated in this slice because no general audit/log compatibility subsystem exists yet.

That omission is explicit and non-blocking for OAuth correctness.

## 18. Approve: authorization code

For:

`response_type=code`

the flow calls existing:

`IssueAuthorizationCode(subject, client_id, effective_scope)`.

On success:

### redirect URI exists

redirect to:

```text
redirect_uri?code=<code>
```

or:

```text
redirect_uri&code=<code>
```

when `?` already exists.

### redirect URI absent

return:

`OAuthAuthorizationCodeDisplay`

and render the code in HTML.

Credential collision rejection remains a typed internal failure and is mapped to a controlled authorization error page rather than leaking an exception.

## 19. Approve: implicit token

For:

`response_type=token`

the flow calls existing:

`IssueImplicitApiAccessToken(subject, client_id, effective_scope)`.

Redirect URI is guaranteed by request validation.

Success redirects:

```text
redirect_uri#access_token=<token>
```

No `token_type`, `scope`, `expires_in` or state parameter is added because 4.2.0 does not emit them.

## 20. Authenticated deny

Authenticated consent denial is distinct from the outer cancel branch.

For token:

```text
redirect_uri#error=access_denied
```

For code with redirect URI:

```text
redirect_uri?error=access_denied
```

or `&error=...` when needed.

For code without redirect URI:

- render HTML error page;
- error code `access_denied`;
- human text corresponds to revoked/denied API access for the client.

No framework JSON error is produced in this case because the legacy action renders `ApiError`.

## 21. Redirect policy seam

Webasyst 4.2.0 does not register OAuth clients and does not validate redirect URIs.

This behavior MUST NOT become an assumed invariant of OAuth application logic.

Application-owned port:

`OAuthRedirectPolicy`

First compatibility implementation:

`LegacyUnregisteredRedirectPolicy`

It accepts the supplied redirect URI subject only to basic representability/serialization constraints required by the Python framework.

Future:

`RegisteredClientRedirectPolicy`

may validate registered client/redirect pairs without changing authorization orchestration or credential storage.

This slice deliberately preserves legacy open redirects only inside the compatibility policy.

## 22. /api.php/token

`/api.php/token` is a thin HTTP compatibility adapter over:

`ExchangeAuthorizationCode`.

It is not part of the browser consent Composite.

Required POST fields:

- `code`;
- `client_id`;
- `grant_type`.

`grant_type` must equal:

`authorization_code`.

Required-field checks use PHP-falsy semantics and read POST only.

Mappings:

- missing required field → `invalid_request`;
- unsupported grant type → `unsupported_grant_type`;
- missing code → `invalid_grant`;
- client mismatch → `invalid_grant`;
- expired code → `invalid_grant`;
- success → payload containing only `access_token`.

No authorization code consumption is introduced; existing ADR-032 compatibility policy remains authoritative.

## 23. Token endpoint response semantics

The legacy token controller writes a body through `waAPIDecorator` and does not set explicit failure HTTP status.

Therefore all ordinary token-controller outcomes in this slice use HTTP 200, including:

- `invalid_request`;
- `unsupported_grant_type`;
- `invalid_grant`;
- invalid explicit response format.

Response format:

- default JSON;
- `format=json`;
- `format=xml`;
- invalid explicit format → JSON `invalid_request` payload with description `Invalid format: <FORMAT>`.

JSONP is NOT applied to token controller responses.

The existing JSON/XML formatter Services may be reused for serialization, but controller-level format selection needs a compatibility Service with the exact legacy error text/status semantics.

## 24. /api.php/revoke authentication

Legacy revoke first calls outer:

`waAPIController::checkToken()`.

Therefore the request MUST authenticate before reaching revoke action. Controller-level `format` handling occurs only after this authentication succeeds. Missing/invalid token failures are framework `waAPIException` responses and retain framework format/status/JSONP semantics; an invalid controller `format` cannot override a prior `token_required` or `invalid_token` failure.

Authentication credential precedence is the existing legacy API credential extraction order:

1. request `access_token` (POST shadows GET);
2. Authorization header;
3. server `HTTP_AUTHORIZATION`.

Bearer prefix stripping remains case-insensitive for header sources.

Authentication uses existing:

`ResolveApiAccessToken`.

It also performs the same API-user activity compatibility touch used by authenticated API method execution.

A small application Composite:

`OAuthRevokeAuthenticationFlow`

sequences:

```text
ResolveApiAccessToken
      ↓
API user compatibility activity touch
      ↓
authenticated revoke subject
```

It does not itself choose which token to delete.

## 25. Revoke target quirk

After outer authentication, `webasystApiRevokeController` separately executes:

```php
waRequest::request('access_token', '', 'string')
```

and deletes that value.

This creates a source-backed quirk:

### request token supplied

The request token wins during outer authentication and is also the revoke target.

If invalid, the request fails during authentication before the revoke controller.

### header-only Bearer token

The Bearer token authenticates successfully.

The controller-level request target is empty.

Legacy behavior:

- deletion is a no-op;
- response is `{"access_token": ""}`;
- the valid Bearer token remains stored.

The Python design preserves this behavior without constructing an invalid empty `ApiAccessToken`.

Compatibility target normalization yields:

- `RevokeTargetProvided(ApiAccessToken)`;
- `RevokeTargetMissing`.

`RevokeTargetMissing` means skip `RevokeApiAccessToken` and emit empty access-token response.

This quirk is isolated in Webasyst compatibility code and is not part of the generic revocation use case.

## 26. Revoke endpoint response semantics

After successful outer authentication, revoke controller behavior is:

- default JSON;
- optional XML;
- invalid explicit format → JSON `invalid_request`;
- ordinary controller outcomes are HTTP 200;
- no JSONP.

Before successful authentication, framework-level API exception formatting remains in effect, including framework JSON/XML selection and JSONP behavior when requested.

When a request target exists:

- call existing `RevokeApiAccessToken`;
- both revoked and already-missing compatible outcomes return the same request token in the response.

The authentication step prevents the normal request-target case from reaching an already-missing target unless concurrent state changes occur.

Infrastructure failures remain exceptional.

## 27. Shared API transport preconditions

All three endpoints reuse existing:

`LegacyApiTransportPreconditionService`.

Order remains:

```text
API disabled
      ↓
HTTPS-required redirect
      ↓
OAuth endpoint behavior
```

Disabled API:

- legacy framework error `disabled`;
- HTTP 404.

HTTPS policy:

- 301 redirect to the same request URL under HTTPS.

No OAuth-specific duplicate API-enabled setting is created.

## 28. Presentation routing

New presentation module:

`presentation/http/legacy_oauth.py`

It exposes static routes:

- `/api.php/auth`;
- `/api.php/token`;
- `/api.php/revoke`.

These routes MUST be registered before the existing:

`/api.php/{api_path:path}`

method-execution catch-all.

Reserved OAuth paths must never reach `ApiMethodRegistry`.

The existing method-execution router remains responsible only for generic API method execution.

## 29. HTML surface

The first OAuth HTML surface is intentionally minimal and functional.

States:

- login;
- consent;
- authorization code display;
- error.

It is not a recreation of Smarty/Webasyst styling.

Requirements:

- valid HTML;
- UTF-8;
- all request-derived text escaped;
- form methods/actions explicit;
- OAuth query state preserved;
- CSRF hidden field present;
- approve/deny/logout controls distinct;
- no JavaScript required for core flow.

A later UI modernization may replace the renderer without changing application Composites.

## 30. Error model

Application-level expected outcomes remain typed.

Authorization flow distinguishes at least:

- consent required;
- code granted;
- implicit token granted;
- authenticated denial;
- invalid effective scope;
- credential issuance unavailable.

Transport/compatibility additionally distinguishes:

- malformed request;
- cancel redirect/error;
- unauthenticated login state;
- CSRF rejection;
- redirect response;
- HTML error response;
- token controller payload;
- revoke controller payload.

Infrastructure failures such as DB/session backend failures remain exceptions.

## 31. Security boundaries

- OAuth application code receives no FastAPI/Starlette Request;
- password values remain `SecretStr`;
- raw access tokens/codes are not logged;
- raw session/persistent credentials are not logged;
- client name is HTML-escaped;
- app names are HTML-escaped;
- redirect behavior is behind `OAuthRedirectPolicy`;
- open legacy redirect acceptance is compatibility-only;
- CSRF is checked before authenticated POST approve/deny/logout;
- cancel-before-auth intentionally preserves source behavior;
- no client registry is fabricated in this compatibility slice;
- no dynamic app imports are introduced.

## 32. Testing strategy

### 32.1 Characterization tests

Pin source-backed behavior:

- required auth query fields;
- token response type requires redirect URI;
- cancel occurs before auth/CSRF;
- query vs fragment redirects;
- code display without redirect URI;
- scope silently drops missing/unauthorized apps;
- empty effective scope errors;
- authenticated logout occurs before scope evaluation;
- token controller POST-only required fields;
- token controller HTTP-200 errors;
- revoke header-only authentication no-op deletion quirk;
- request access token precedence over Bearer;
- default JSON and XML selection.

### 32.2 Unit tests

Pin:

- Entity/VO taxonomy;
- catalog lookup;
- consent access policy;
- scope filter order/deduplication;
- authorization Composite grant/deny states;
- redirect policy outputs;
- CSRF issue/validation;
- token error mapping;
- revoke target extraction;
- revoke authentication sequencing.

### 32.3 HTTP tests

Pin:

- GET login surface;
- password login → session cookie → consent;
- consent approve code redirect;
- code display;
- implicit token fragment redirect;
- deny redirects;
- cancel pre-auth;
- logout clears auth cookies;
- `/api.php/token` JSON/XML;
- `/api.php/revoke` request token and Bearer-only quirk;
- static OAuth routes take precedence over generic API catch-all.

### 32.4 Vertical integration

Use real SQLite:

1. seed backend user and rights;
2. seed/install consent catalog fixture apps;
3. open auth URL unauthenticated;
4. login through backend bridge;
5. render filtered consent;
6. approve code;
7. exchange code through `/api.php/token`;
8. call/revoke token through supported request-token path;
9. verify token persistence state;
10. separately verify header-only revoke leaves token intact.

## 33. Architecture guards

Reject:

- FastAPI/Starlette imports below `application/oauth_authorization`;
- SQLAlchemy imports below application OAuth package;
- compatibility imports below application OAuth package;
- raw cookie names in application OAuth code;
- HTML templates/markup in application OAuth code;
- dynamic app loading;
- `None` operation states;
- raw string response-type/grant-type discriminators where `EnumStr` exists;
- OAuth client registry introduced inside this slice;
- PKCE/refresh-token fields entering compatibility contracts;
- `token-headless` implementation entering the branch.

## 34. Composition

New `OAuthAuthorizationComponents` wires:

- backend session bridge;
- authorization code issuer;
- implicit token issuer;
- authorization code exchange;
- access token resolver;
- access token revoker;
- consent app catalog;
- consent access policy;
- redirect policy;
- CSRF Service;
- shared API preconditions;
- API activity compatibility touch;
- response serializers/renderers.

The Container exposes the composed OAuth surface as one component rather than adding another flat collection of transport helpers.

## 35. Acceptance criteria

The slice is accepted when:

1. unauthenticated `/api.php/auth` can log in through the existing backend auth core;
2. current subject is resolved only through the backend session bridge;
3. requested scope is filtered exactly through installed-app/catalog + backend-right semantics;
4. consent can approve code/token and deny access with legacy redirect behavior;
5. outer cancel remains distinct and precedes auth/CSRF;
6. authenticated logout clears backend credentials and returns to authorization flow;
7. `/api.php/token` exchanges existing 4.2.0-compatible authorization codes;
8. token endpoint controller errors remain HTTP 200;
9. `/api.php/revoke` preserves both normal request-token deletion and header-only no-op quirk;
10. OAuth static routes cannot fall through to generic API method dispatch;
11. application OAuth code remains HTTP/ORM/HTML-free;
12. full repository compile/tests are green.

## 36. Explicit non-goals

Do not implement in this slice:

- token-headless;
- Webasyst ID;
- social OAuth;
- client registration;
- redirect URI registration;
- PKCE;
- refresh tokens;
- OAuth state parameter extensions;
- OIDC;
- app filesystem discovery;
- PHP session decoding;
- audit-log subsystem migration;
- full Webasyst visual styling.

Those remain separate independently reviewable slices.
