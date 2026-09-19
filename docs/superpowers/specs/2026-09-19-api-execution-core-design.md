# API Execution Core Design

Status: accepted
Date: 2026-09-19
Branch: `feature/api-execution-core`
Target: Webasyst Framework 4.2.0 API execution compatibility

## Goal

Build the Webasyst-compatible API execution layer on top of the already implemented OAuth2 credential core and access-control subsystem.

This slice handles authenticated API method invocation:

```text
HTTP compatibility request
    -> normalize target / format / credential input / parameters
    -> resolve API access token
    -> authorize app access + scope + license
    -> resolve registered API method
    -> validate HTTP method
    -> execute method
    -> render legacy JSON / XML / JSONP response
```

The slice does not implement `/api.php/auth` consent/redirect/CSRF flows. OAuth authorization UI is a later subsystem.

## Architectural taxonomy: Entity / VO / Services / Composite

All new API Execution Core domain/application code must be classified explicitly into one of four categories. This taxonomy is mandatory for the subsystem and works inside the repository's existing layer boundaries; it does not replace ports, infrastructure adapters, compatibility adapters, presentation, or composition root.

### Entity

An Entity has stable identity and represents a domain object whose identity matters independently of the current values attached to it.

Initial entity:

```text
ApiMethodDefinition
    identity: ApiMethodTarget
    allowed_http_methods
    handler
```

`ApiMethodDefinition` is the canonical registered method entity. The registry is keyed by its `ApiMethodTarget` identity. Adding an API method creates/registers another entity; central dispatch code does not gain another branch.

Do not invent entities for immutable scalar concepts merely to populate the category. Contacts/users/tokens remain owned by their existing subsystems.

### VO — Value Objects

VOs are immutable, validated, equality-by-value objects. Internal VOs use `@dataclass(slots=True, frozen=True)` unless they cross a serialized boundary that requires Pydantic.

Initial VOs/composed values include:

```text
ApiMethodName
ApiMethodTarget
ApiHttpMethod
ApiParameterName
ApiParameterMap
ApiRequestParameters
ApiJsonpCallback
ApiInvocationStatus
```

Existing values reused directly:

```text
AppId
ApiAccessToken
ApiClientId
ApiScope
AuthenticatedSubject
```

Open extension identifiers remain open VOs:

- `AppId`
- `ApiMethodName`
- `ApiHttpMethod` — normalized uppercase HTTP token, because HTTP method tokens are extensible protocol identifiers rather than a closed discriminator domain.

Closed serialized state/discriminator domains use `EnumStr`:

- `ApiResponseFormat` (`json`, `xml`)
- framework rejection/result kinds
- credential source kinds
- authorization decision kinds
- method lookup/result kinds

### Services

A Service owns one coherent rule or operation and is stateless apart from injected dependencies. Services do not act as dependency containers.

Initial services:

```text
ApiCredentialExtractionService        # compatibility/presentation
ApiResponseFormatService              # compatibility/presentation
ApiRequestAuthorizer                  # application
ApiMethodExecutor                     # application
ApiParameterReaderService             # compatibility helper for legacy get/post semantics
ApiUserActivityService                # application boundary with persistence adapter
LegacyApiResponseFormatter            # compatibility/presentation
```

A service must not accumulate multiple pipeline phases just because they occur sequentially.

### Composite

A Composite combines already defined Entities, VOs and Services into a larger execution unit. It contains orchestration, not primitive business rules. This category is deliberately not a service locator and is not a recreation of `waSystem`.

Initial composites:

```text
ApiInvocationRequest
ApiPrincipalContext
ApiInvocationContext
ApiAuthorizationComposite
ApiExecutionPipeline
ApiExecutionResult
ApiTransportResponse
```

`ApiExecutionPipeline` is the top-level application orchestration composite. It delegates credential resolution, authorization, registry lookup and execution to smaller services/ports.

## Layer boundaries

The Entity/VO/Services/Composite taxonomy applies to domain/application concepts. Existing dependency direction remains mandatory:

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

Examples:

- SQLAlchemy rows are infrastructure adapters, not Entities in the API domain taxonomy.
- FastAPI/Starlette request/response objects stay in presentation.
- JSON/XML/JSONP rendering belongs to compatibility/presentation Services.
- `ApiExecutionPipeline` may depend on application ports/services; it may not import FastAPI, SQLAlchemy, Webasyst compatibility implementations or global registries.

This slice does not trigger a repository-wide relocation of already completed subsystems. The taxonomy is mandatory for all new API Execution Core code and any existing API execution code touched by this slice.

## Source-backed Webasyst 4.2.0 behavior

The supplied 4.2.0 source is authoritative.

### Request routes

`waAPIController::dispatch()` supports three execution forms:

```text
/api.php?app=shop&method=order.get
/api.php/shop/order.get
/api.php/shop.order.get
```

All three normalize into one typed target:

```text
ApiMethodTarget(
    app_id=AppId("shop"),
    method=ApiMethodName("order.get"),
)
```

Malformed execution URLs produce framework `invalid_request`.

Special endpoints such as `/api.php/auth`, `/api.php/token`, `/api.php/revoke`, `token-headless`, cron and profile/license helpers are not method-target routes. `/api.php/token` and revoke will later delegate to the already implemented credential core; `/api.php/auth` is explicitly a later consent-flow slice.

### Global API disable and HTTPS redirect

Before execution, legacy dispatch:

- rejects all API use with `disabled` / HTTP 404 when Webasyst `disable_api` is configured;
- redirects to HTTPS with HTTP 301 when domain `ssl_all` is enabled and the incoming request is not HTTPS.

These are presentation/compatibility policies, not application method-execution rules.

### Response format

Query `format` accepts only JSON/XML, case-insensitively through uppercase normalization.

The compatibility adapter normalizes to:

```text
ApiResponseFormat.JSON
ApiResponseFormat.XML
```

An invalid explicit format yields legacy `invalid_request` payload semantics with HTTP status 200 because 4.2.0 calls the response helper without an explicit error status. The application pipeline never branches on raw strings such as `"JSON"` or `"XML"`.

### Access-token extraction precedence

`waAPIController::checkToken()` resolves credential input in this order:

1. request parameter `access_token` (legacy `waRequest::request`, therefore merged request input);
2. `Authorization` header from `getallheaders()`;
3. `HTTP_AUTHORIZATION` server value;
4. strip a leading Bearer prefix case-insensitively and trim.

Missing credential -> `token_required`, HTTP 400.

Invalid credential -> `invalid_token`, HTTP 401. Legacy response includes SHA-256 of the supplied invalid token for a non-matching lookup; this field is compatibility-output behavior and raw tokens must never be logged.

Expired credential -> `invalid_token`, HTTP 401.

Actual token validation and `last_use_datetime` touch are delegated to the existing `ResolveApiAccessToken` use case. The new execution layer must not query `wa_api_tokens` directly.

### Authenticated API principal

Successful token resolution provides:

```text
contact_id
client_id
scope
```

The execution pipeline represents this as `ApiPrincipalContext` composite. It does not mutate a global `wa()->setUser()` equivalent.

Legacy also updates the contact's `last_datetime` when the previous activity timestamp is more than 30 seconds old. Preserve this as a separately injected `ApiUserActivityService`; it must not be hidden inside token resolution or method registry logic.

### Authorization order

Legacy `execute()` checks, in order:

1. app exists;
2. backend app access;
3. token scope contains app;
4. app license is not blocked;
5. initialize app;
6. resolve method class;
7. method validates HTTP verb;
8. execute method.

The Python pipeline preserves observable rejection order.

Application authorization service:

```text
ApiRequestAuthorizer
    -> InstalledAppDirectory
    -> ApiAppAccessPolicy / existing access-control capability
    -> token scope
    -> AppLicensePolicy
```

Expected negative decisions are typed results, never exceptions/None/bools.

### App access compatibility

Legacy `hasAppAccess()`:

- denies contacts whose `is_user <= 0`;
- grants authenticated backend users access to `webasyst` itself;
- for any other app requires effective app `backend > 0`.

Represent this through `ApiAppAccessPolicy`, not a hard-coded `if app == "webasyst"` inside the execution pipeline.

The policy may reuse the existing access-control subsystem and subject resolution ports.

### Scope

The resolved `ApiScope` must include the target `AppId`. Missing target app in scope -> `access_denied`, HTTP 403.

Raw legacy comma-separated scope strings never enter this layer; they are already normalized by the credential adapter.

### License

Legacy `hasAppLicense()` allows execution when installer is absent. When installer exists, a blocking announcement for the target app causes `payment_required`, HTTP 402.

Application owns:

```text
AppLicensePolicy
    -> AppLicenseGranted
    -> AppLicenseBlocked
```

Until installer migration exists, composition uses an explicit allow policy. This is a deliberate adapter choice, not an implicit `None` dependency or hard-coded shortcut inside `ApiRequestAuthorizer`.

### Method discovery

Legacy computes a PHP class name dynamically:

```text
$app + ucfirst(each dot-separated method segment) + "Method"
```

and then calls `class_exists()`.

Python must not reproduce dynamic class-name lookup.

Application-owned method registry:

```python
class ApiMethodRegistry(Protocol):
    def resolve(self, target: ApiMethodTarget) -> ApiMethodResolution: ...
```

Results:

```text
ApiMethodRegistered(definition)
ApiMethodMissing(target)
```

`ApiMethodDefinition` Entity contains:

```text
target
allowed_methods
handler
```

Adding a new API method requires entity registration, not an `if/elif` branch in the pipeline.

### HTTP verb check

Legacy `waAPIMethod` defaults to GET and may declare one or multiple allowed methods. Request method is normalized uppercase and mismatch yields `invalid_request` / HTTP 405.

`ApiHttpMethod` remains an open uppercase VO; each `ApiMethodDefinition` contains a non-empty immutable collection of allowed methods.

`ApiMethodExecutor` performs the verb check before invoking the handler.

### Method handler

Handler port:

```python
class ApiMethodHandler(Protocol):
    async def execute(
        self,
        context: ApiInvocationContext,
        parameters: ApiRequestParameters,
    ) -> ApiMethodResult: ...
```

Handlers receive no Starlette/FastAPI request object, ORM session, global current user or global application object.

`ApiInvocationContext` composite includes:

```text
principal
method target
resolved method identity
```

Request transport metadata not needed by business execution is kept out of the handler context.

### Query/form parameter semantics

Legacy `waAPIMethod::get()` and `post()` preserve source distinction and consider a required value missing when the returned PHP value is falsy.

Do not collapse query/form into one anonymous dictionary if compatibility handlers need to distinguish them.

VO/composite model:

```text
ApiParameterMap
ApiRequestParameters(
    query,
    form,
)
```

`ApiParameterReaderService` implements the legacy `get/post(required=...)` compatibility semantics for migrated legacy methods. New native API methods may validate typed request DTOs independently rather than using legacy falsy semantics.

### Rights from a method

Legacy `waAPIMethod::getRights(name)` reads rights for the currently initialized application through global user state.

Python handlers do not get a global user. When a method needs a named right, it uses injected access-control application services/ports and the `ApiPrincipalContext` contact identity + target `AppId`.

### Method result

Application handler returns framework-agnostic typed result:

```text
ApiMethodSucceeded(payload, status_code)
ApiMethodRejected(error)
```

Payload is JSON-compatible data. Method/application errors may use open application-specific error identifiers; framework-level rejection codes remain closed `EnumStr` domains.

## Framework error model

Framework error codes characterized from 4.2.0 include:

```text
disabled
invalid_request
token_required
invalid_token
app_not_installed
access_denied
payment_required
invalid_method
invalid_param
```

Use closed `ApiFrameworkErrorCode(EnumStr)` for these framework-owned codes.

An application handler may need custom errors, so app-defined codes use an open immutable `ApiApplicationErrorCode` VO rather than extending the framework enum.

Framework error composite:

```text
ApiFrameworkError(
    code,
    description,
    http_status,
    details,
)
```

No expected application/framework rejection is represented by exceptions. Infrastructure failures remain exceptional.

## Response rendering compatibility

Rendering is outside application execution.

### JSON

Legacy JSON recursively removes every `_element` key before serialization. Preserve this behavior in `LegacyJsonApiFormatter`.

### XML

Legacy XML:

- root element is `<response>`;
- `_element` optionally controls list item element names;
- plural keys may infer singular child names (`items -> item`, `categories -> category`);
- associative arrays become nested elements;
- scalar values become text nodes;
- empty scalar strings create empty elements.

Preserve this through source-backed characterization tests in `LegacyXmlApiFormatter`.

Application handlers do not know about `_element` unless a compatibility-migrated legacy method intentionally returns legacy-shaped payload metadata.

### JSONP

When JSON response has a non-empty GET `callback`:

- HTTP status is forced to 200, including error responses;
- content type becomes JavaScript;
- output is `callback(<json>);`.

JSONP is a compatibility presentation feature only. It is not part of `ApiMethodResult`.

`ApiJsonpCallback` is an immutable VO at the presentation boundary. Exact 4.2.0 behavior does not validate callback syntax; the compatibility implementation preserves source behavior for the legacy endpoint while native APIs do not expose JSONP.

## Transport composites

Presentation normalizes raw HTTP into transport composites before calling application services. The ASGI adapter also normalizes any server-provided `HTTP_AUTHORIZATION` compatibility value into the same explicit authorization-header state instead of dropping that fallback.

```text
LegacyApiHttpRequestComposite
    target input
    credential inputs
    query parameters
    form parameters
    HTTP method
    requested response format
    JSONP callback
```

Application receives a smaller `ApiInvocationRequest` composite containing only normalized domain/application values.

Application does not receive headers, ASGI scope or request objects.

## Execution pipeline composite

`ApiExecutionPipeline` orchestration:

```text
ApiInvocationRequest
    -> ResolveApiAccessToken
        missing/expired -> framework credential rejection
    -> ApiUserActivityService
    -> ApiRequestAuthorizer
        app missing/access/scope/license -> typed rejection
    -> ApiMethodRegistry.resolve
        missing -> invalid_method
    -> ApiMethodExecutor
        verb mismatch -> invalid_request / 405
    -> ApiMethodHandler.execute
    -> ApiExecutionResult
```

The pipeline owns sequencing only. It does not contain SQL, format rendering, dynamic imports, access-right calculations or handler-specific parameter parsing.

## Proposed package layout

New subsystem files must make the Entity/VO/Services/Composite classification obvious:

```text
src/gomazon_webasyst/
  application/
    api_execution/
      entities/
        method_definition.py
      vo/
        method.py
        parameters.py
        errors.py
      services/
        authorizer.py
        method_executor.py
        activity.py
      composites/
        invocation.py
        authorization.py
        pipeline.py
        results.py
    ports/
      api_method_registry.py
      installed_apps.py
      app_license.py
      api_activity.py
      api_app_access.py

  contracts/
    api_execution.py

  compatibility/webasyst/api/
    vo/
      transport.py
    services/
      credential_extractor.py
      target_parser.py
      parameter_reader.py
      response_format.py
      json_formatter.py
      xml_formatter.py
      error_mapper.py
    composites/
      http_adapter.py

  infrastructure/
    api_execution/
      method_registry.py
      app_directory.py
      activity.py

  presentation/http/
    legacy_api.py

  composition/
    api_execution.py
```

The exact number of files may be adjusted during implementation if individual files remain focused. Do not collapse the subsystem back into a single `api_execution.py` god-module.

## Application-owned ports

### Installed app directory

```text
InstalledAppResolved
InstalledAppMissing
```

`InstalledAppDirectory.resolve(AppId)` must be extensible and separate from method registration.

### Method registry

```text
ApiMethodRegistered
ApiMethodMissing
```

Registry implementations may be in-memory at first. Application code never performs imports/class-name construction from request strings.

### License policy

```text
AppLicenseGranted
AppLicenseBlocked
```

### App access policy

```text
ApiAppAccessGranted
ApiAppAccessDenied
ApiAppSubjectUnavailable
```

Detailed internal access-control reasons may be coarsened into legacy `access_denied` at the compatibility boundary.

### Activity

Activity side-effect port/service updates user last activity according to the characterized 30-second legacy threshold. A no-op/native policy may be injected where this compatibility side effect is not required.

## API enabled / HTTPS policies

Global API enabled state and forced-HTTPS redirect are compatibility/presentation preconditions. They run before credential extraction/pipeline execution.

Ports/configuration should permit:

```text
ApiEnabled
ApiDisabled(message)

HttpsAccepted
HttpsRedirect(location)
```

Do not put domain/host URL reconstruction into application services.

## Security properties

- never log raw API access tokens;
- invalid-token SHA-256 echo exists only in Webasyst compatibility output;
- application pipeline consumes already normalized `ApiAccessToken`;
- application handlers receive principal identity/scope, not bearer text;
- dynamic class imports from request method names are forbidden;
- SQLAlchemy and FastAPI/Starlette are forbidden from application API execution packages;
- method registry registration is explicit;
- unknown app/method/access/scope/license outcomes are typed;
- application-specific errors remain open identifiers without weakening framework closed discriminators;
- JSONP is legacy-only and never enabled for native endpoints implicitly.

## Scope boundaries

Included:

- `/api.php` API method target parsing for the three 4.2.0 execution forms;
- token extraction compatibility;
- reuse of `ResolveApiAccessToken`;
- installed-app, app-access, scope and license authorization pipeline;
- explicit method registry;
- HTTP method validation;
- method handler protocol;
- query/form parameter source preservation;
- legacy parameter-reader helper semantics;
- API user activity touch service;
- JSON, XML and JSONP formatting;
- legacy error mapping/envelopes;
- API enabled / HTTPS redirect compatibility policies;
- ASGI compatibility adapter for method execution only.

Not included:

- `/api.php/auth` consent UI;
- OAuth approve/deny redirects;
- OAuth CSRF;
- requested-scope consent filtering;
- client app metadata/catalog UI;
- Webasyst ID/social login;
- token-headless;
- license-cache/profile-update helpers;
- cron API dispatch;
- Redis/Supabase session-state adapters;
- installer announcement subsystem itself;
- migration of every bundled app API method.

The slice will include one or more explicit test API methods/fixture registrations to prove dispatch without pretending all bundled Webasyst app APIs are already migrated.

## Characterization tests

Source-backed tests cover:

- three method-route forms and malformed request;
- format normalization JSON/XML and invalid format;
- access-token input precedence;
- case-insensitive Bearer stripping;
- missing token -> `token_required`/400;
- invalid token -> `invalid_token`/401 + compatibility SHA-256 detail;
- expired token behavior delegated through credential core;
- authorization order: app exists -> app access -> scope -> license -> method;
- `webasyst` app access exception;
- method class-name source behavior as evidence for registry replacement;
- HTTP verb default GET and multiple allowed verbs;
- GET vs POST parameter source distinction;
- legacy required-param falsy semantics;
- 30-second last-activity threshold;
- JSON `_element` removal;
- XML root/list/plural/`_element` behavior;
- JSONP forces status 200 and wraps both success/error JSON;
- error envelope shape and relevant HTTP status mapping;
- API disable and HTTPS redirect preconditions.

## Unit tests

### Entity / VO

- `ApiMethodDefinition` identity is `ApiMethodTarget`;
- open VOs reject empty/invalid values and are frozen/hashable;
- `ApiResponseFormat` and framework result/error discriminators derive from `EnumStr`;
- request parameter composites preserve source.

### Services

- authorizer rejects in the exact legacy order;
- app-access compatibility policy handles non-user, webasyst exception and normal backend access;
- method executor rejects disallowed verb before handler call;
- parameter reader preserves GET/POST and required falsy semantics;
- activity service honors >30 second threshold;
- response format/extractor services normalize raw transport once.

### Composite

- pipeline sequences credential -> activity -> authorization -> registry -> executor;
- negative result stops later stages;
- no composite contains concrete persistence/HTTP dependencies;
- method registry extension requires registration only.

## Integration tests

SQLite/ASGI vertical path:

1. seed API token + user/access state;
2. register one fixture app and one fixture method;
3. invoke each supported legacy route form;
4. verify query token and Bearer token paths;
5. verify scope/access denial;
6. verify method 405;
7. verify token `last_use_datetime` and user activity touch;
8. verify JSON output;
9. verify XML output;
10. verify JSONP status/content behavior;
11. verify method-not-found and app-not-installed envelopes.

No `/api.php/auth` flow is required for this slice.

## Architecture tests

Guards must reject:

- FastAPI/Starlette imports in `application/api_execution`;
- SQLAlchemy imports in application/contracts;
- compatibility imports from application API execution code;
- dynamic `importlib`/class-name lookup in method resolution;
- raw `wa_api_tokens` or legacy table names in execution application code;
- `T | None`/`Optional` as lookup/result/lifecycle state;
- raw string discriminators where a closed `EnumStr` domain exists;
- application handlers accepting HTTP request/session/ORM types;
- a central provider/method `if app == ... and method == ...` dispatch chain;
- new API Execution Core application code that cannot be classified into Entity, VO, Service or Composite.

## Composition

New composition root constructs:

```text
ApiExecutionUseCases / ApiExecutionComposite
    ResolveApiAccessToken        # existing
    ApiUserActivityService
    ApiRequestAuthorizer
    ApiMethodRegistry
    ApiMethodExecutor
    ApiExecutionPipeline
```

Compatibility/presentation composition constructs formatters and HTTP adapter separately.

A fixture/default method registry may initially be empty in production composition. Tests register explicit methods. Bundled app registrations are later product/application migration slices.

## Acceptance criteria

The slice is implementation-ready when the written plan can prove:

- every new domain/application API execution type is explicitly placed under Entity, VO, Services or Composite;
- the taxonomy does not weaken Ports/DI/infrastructure/presentation boundaries;
- legacy method requests normalize into one target/pipeline;
- token resolution reuses the existing OAuth credential core;
- authorization order matches 4.2.0;
- dynamic PHP method class discovery is replaced by explicit registry entities;
- GET/POST parameter source semantics are not lost;
- JSON/XML/JSONP behavior is isolated from application execution;
- `/api.php/auth` remains out of scope;
- architecture tests make a future god-controller regression difficult.