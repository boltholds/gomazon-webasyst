# Webasyst Routing & Dispatch Compatibility — Design Specification

Status: accepted design baseline
Date: 2026-09-14
Repository: `boltholds/gomazon-webasyst`

## 1. Goal

Implement Webasyst 4.2.0 routing and front-controller compatibility in Python without reproducing PHP global state, dynamic class loading, or nullable dictionary-shaped state throughout the new runtime.

The compatibility subsystem must preserve externally relevant Webasyst behavior while converting legacy route configuration into closed, typed Pydantic variants at the compatibility boundary.

The central invariant is:

> Nullable/optional fields must not encode mutually exclusive architectural states. Use discriminated unions and normalize legacy input at compatibility boundaries. `None` is allowed only when absence itself is a valid domain value.

This invariant applies beyond routing and is recorded in `AGENTS.md`.

## 2. Sources of truth

Compatibility decisions are derived from two sources:

1. The supplied Webasyst Framework 4.2.0 source archive.
2. Official Webasyst developer documentation: `https://developers.webasyst.com/docs`.

When current documentation and the supplied 4.2.0 source disagree, the 4.2.0 source is authoritative for this migration unless an explicit ADR chooses newer behavior.

Relevant official documentation:

- Frontend routing: `https://developers.webasyst.com/docs/cookbook/basics/routing/`
- Backend routing: `https://developers.webasyst.com/docs/cookbook/backend-routing/`
- Naming rules: `https://developers.webasyst.com/docs/basics/naming-rules/`
- Framework basics/request lifecycle: `https://developers.webasyst.com/docs/basics/`

Relevant 4.2.0 source:

- `wa-system/routing/waRouting.class.php`
- `wa-system/controller/waFrontController.class.php`

### Documentation discrepancy: dispatch order

Current naming-rules documentation describes `Controller -> Actions -> Action`, while backend/frontend routing documentation and Webasyst 4.2.0 `waFrontController::getController()` use:

1. single `Controller`,
2. single `Action`,
3. multi-action `Actions`,
4. optional fallback to the module default when `try_default` is enabled,
5. 404.

The Python compatibility resolver will preserve the 4.2.0 order:

```text
Controller -> Single Action -> Multi Actions -> optional default fallback -> 404
```

## 3. Non-negotiable modeling rule

Legacy PHP arrays may contain arbitrary combinations of keys such as `app`, `module`, `action`, `plugin`, `redirect`, `code`, `static_content`, and custom route parameters.

Those arrays are untrusted compatibility input. They must not become application contracts.

Bad target model:

```python
class RouteRule(BaseModel):
    app: str | None = None
    module: str | None = None
    action: str | None = None
    plugin: str | None = None
    redirect: str | None = None
    code: int | None = None
```

This encodes several unrelated states in one object and forces runtime `None` checks everywhere.

The required flow is:

```text
legacy dict / shorthand string
          |
          v
LegacyRouteParser
          |
validation + normalization
          |
          v
closed discriminated-union variants
          |
          v
matcher / resolver / dispatcher
```

Only the parser/normalizer is allowed to inspect arbitrary legacy keys.

## 4. Separate routing stages

Webasyst frontend routing is two-stage:

1. system/domain routing selects a settlement/application and records settlement route parameters;
2. application routing resolves the remaining path into a concrete module/action/plugin dispatch request.

These are distinct state types. The first stage must not return a partially populated final dispatch object.

```text
FrontendRouteRequest
        |
        v
SystemRouteResolver
        |
        v
SettlementResolution
        |
        v
AppRouteResolver
        |
        v
DispatchRequest
```

Backend routing uses a separate request type and resolver because Webasyst backend has a known app namespace and different defaults/query semantics.

```text
BackendRouteRequest
        |
        v
BackendRouteResolver
        |
        v
DispatchRequest
```

## 5. Request contracts

Frontend and backend request shapes are separate contracts rather than one request with an `environment` switch.

```python
from pydantic import BaseModel, ConfigDict


class FrontendRouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    domain: str
    path: str
    query: dict[str, str]


class BackendRouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    app: str
    path: str
    query: dict[str, str]
```

Transport-specific request objects such as Starlette `Request` do not cross into the routing compatibility core.

## 6. Route pattern representation

Legacy Webasyst patterns support:

- literal paths,
- `*` wildcards,
- `<name>` captures,
- `<name:regex>` captures,
- route ordering,
- shorthand route values.

The parser compiles a legacy URL expression once into a normalized pattern contract.

```python
class RouteCapture(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    regex: str


class RoutePattern(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str
    regex_source: str
    captures: tuple[RouteCapture, ...]
```

Compiled `re.Pattern` objects may be cached internally by the matcher, but they are not cross-layer contracts.

## 7. System route variants

System/domain routing does not produce a final module/action request. It produces one of a small set of outcomes.

```python
class AppSettlement(BaseModel):
    kind: Literal["app"] = "app"
    app: str
    matched_prefix: str
    route_params: dict[str, str]


class RedirectSettlement(BaseModel):
    kind: Literal["redirect"] = "redirect"
    location: str
    status_code: Literal[301, 302]


SettlementResolution = Annotated[
    AppSettlement | RedirectSettlement,
    Field(discriminator="kind"),
]
```

Static-content routes are intentionally excluded from the first routing/dispatch slice and will get their own explicit variant when migrated. They must not be represented as `static_content: str | None` on a generic route object.

System route configuration is likewise parsed into rule variants rather than one nullable model:

```python
SystemRouteRule = Annotated[
    AppSettlementRule | RedirectRule,
    Field(discriminator="kind"),
]
```

## 8. Dispatch namespace variants

Plugin dispatch is a different namespace, not an optional field on an app namespace.

```python
class AppNamespace(BaseModel):
    kind: Literal["app"] = "app"
    app: str


class PluginNamespace(BaseModel):
    kind: Literal["plugin"] = "plugin"
    app: str
    plugin: str


DispatchNamespace = Annotated[
    AppNamespace | PluginNamespace,
    Field(discriminator="kind"),
]
```

## 9. Dispatch request variants

The presence or absence of an action changes dispatch semantics and therefore is modeled as a variant.

```python
class DefaultDispatch(BaseModel):
    kind: Literal["default"] = "default"
    namespace: DispatchNamespace
    module: str


class ActionDispatch(BaseModel):
    kind: Literal["action"] = "action"
    namespace: DispatchNamespace
    module: str
    action: str


DispatchRequest = Annotated[
    DefaultDispatch | ActionDispatch,
    Field(discriminator="kind"),
]
```

A `DispatchRequest` is fully normalized. It never contains `module=None`, `action=None`, or `plugin=None`.

Frontend defaults such as module `frontend`, and backend defaults such as module `backend`, are applied before constructing this contract.

## 10. App routing rules

Application route configuration is normalized directly to rules that resolve into `DefaultDispatch` or `ActionDispatch`.

The legacy parser handles shorthand such as:

```php
'rss/' => 'frontend/rss'
```

and converts it into an explicit normalized action rule.

No shorthand strings are visible to the matcher or dispatcher.

Route parameters captured from URL placeholders remain explicit route data and are not stored in a process-global request singleton.

## 11. Route matching semantics

The matcher preserves Webasyst 4.2.0 behavior required by the first slice:

- domain-specific routes with `default` fallback,
- aliases resolved before route lookup,
- route list order is significant,
- temporarily-off rules are skipped,
- wildcard matching,
- named regex captures,
- first successful dispatch match wins,
- route-derived parameters override query-derived dispatch parameters where 4.2.0 does so,
- legacy trailing-slash canonicalization can produce a 301 redirect,
- redirect rules default to 301 and use 302 only when explicitly configured as 302.

`priority_settlement`, generated page routes, and static-content routes are outside the first slice.

## 12. Backend normalization

`waFrontController::getDispatchParams()` has backend-specific behavior:

- query may supply `module`, `action`, and `plugin`,
- module defaults to `backend`,
- routing parameters override query parameters,
- if routing supplies a module but not an action, query action is still considered,
- plugin/module/action identifiers are validated against `^[a-z_][a-z0-9_]*$` case-insensitively in PHP.

The Python compatibility normalizer will perform this behavior once and return either `DefaultDispatch` or `ActionDispatch`.

Invalid identifiers produce a typed compatibility error mapped to HTTP 400.

Widgets are excluded from this slice and therefore do not appear as a nullable `widget` field in `DispatchRequest`.

## 13. Dispatch handler registry

PHP 4.2.0 discovers handlers through generated class names and `class_exists()`. Python will preserve the resolution result, not the PHP autoload mechanism.

Handlers are registered explicitly in a typed registry.

Conceptually:

```python
registry.register_controller(key, handler)
registry.register_action(key, handler)
registry.register_actions(key, handler)
```

Registry keys are built from fully normalized namespace/module/action variants.

The resolver checks available handlers in Webasyst 4.2.0 order.

## 14. Dispatch target variants

Handler type determines invocation behavior and is represented by a discriminated union.

```python
class ControllerTarget(BaseModel):
    kind: Literal["controller"] = "controller"
    handler_id: str


class SingleActionTarget(BaseModel):
    kind: Literal["single_action"] = "single_action"
    handler_id: str


class MultiActionTarget(BaseModel):
    kind: Literal["multi_action"] = "multi_action"
    handler_id: str
    action_method: str


DispatchTarget = Annotated[
    ControllerTarget | SingleActionTarget | MultiActionTarget,
    Field(discriminator="kind"),
]
```

There is no nullable `method` field. A controller/single action always uses its known execute entrypoint. Only a multi-actions target carries an action method name because that value is part of its state.

## 15. Handler resolution order

For an explicit action request, resolve in this order:

```text
{namespace}{module}{action}Controller
{namespace}{module}{action}Action
{namespace}{module}Actions::{action}Action
```

For a default request:

```text
{namespace}{module}Controller
{namespace}{module}Action
{namespace}{module}Actions::defaultAction
```

When legacy `try_default` behavior is requested and an explicit action has no handler, the resolver performs one second lookup as `DefaultDispatch` for the same namespace/module.

If no target exists, raise typed `DispatchTargetNotFound` and translate it to 404 in the compatibility HTTP adapter.

## 16. Front-controller overrides

Webasyst allows an application to replace its front controller through `factories.php['front_controller']`.

Python will preserve this extension seam through DI, not dynamic PHP class names.

```text
DispatchStrategyRegistry
    app id -> DispatchStrategy
```

The default strategy uses the standard registry resolver. An app-specific strategy may replace route-to-target resolution for that application.

Application code does not query a global factory or service locator.

## 17. Error model

Compatibility-core errors are framework-agnostic typed errors.

Initial errors:

- `InvalidDispatchParameter` -> 400
- `RouteNotFound` -> 404
- `DispatchTargetNotFound` -> 404
- `PluginUnavailable` -> 404

Authorization errors remain part of the later auth/permissions slice. The routing/dispatch core must expose a seam for authorization but must not implement Webasyst user/session behavior in this slice.

Redirects are successful routing outcomes (`RedirectSettlement`), not exceptions.

## 18. Package boundaries

Target additions:

```text
src/gomazon_webasyst/
  contracts/
    routing.py
    dispatch.py

  application/
    ports/
      dispatch_registry.py

  compatibility/webasyst/
    routing/
      legacy_parser.py
      patterns.py
      system_resolver.py
      app_resolver.py
      backend_resolver.py
    dispatch/
      keys.py
      registry.py
      resolver.py
      strategies.py
      errors.py

  presentation/http/
    legacy_dispatch.py
```

Exact file names may be adjusted during implementation to keep files focused, but dependency direction cannot change.

The compatibility subsystem may depend on contracts/application-owned ports. Application use cases must not import compatibility code.

## 19. Testing strategy

### Parser characterization

Provide representative legacy route arrays/shorthand strings and assert exact normalized union variants.

This is where malformed or ambiguous legacy shapes are rejected.

### Pattern tests

Cover literal patterns, wildcard matching, `<name>`, `<name:regex>`, URL decoding, route order, aliases, and trailing-slash behavior.

### Resolver tests

Test system routing and app routing independently. A system settlement object must never require module/action `None` checks.

### Backend normalization tests

Capture query-vs-route precedence and identifier validation from `waFrontController::getDispatchParams()`.

### Dispatch registry tests

Prove 4.2.0 resolution order:

1. controller,
2. single action,
3. multi actions,
4. optional default fallback,
5. not found.

### Compatibility HTTP tests

Use ASGI tests to prove typed redirect/error/dispatch outcomes without introducing FastAPI into the compatibility core.

### Source-backed characterization

Where behavior is subtle or documentation conflicts with source, record the relevant Webasyst 4.2.0 method/class in the test name or fixture documentation.

## 20. Explicit non-goals for this slice

This slice will not implement:

- Webasyst auth/session/permission checks,
- CSRF handling,
- widgets,
- `priority_settlement`,
- generated page routes,
- static-content route serving,
- sitemap/captcha/payment special dispatch paths,
- PHP autoload/class-name discovery,
- arbitrary plugin lifecycle/locale initialization,
- full URL generation (`waRouting::getUrl`) parity.

Those features require their own compatibility slices or extension variants.

## 21. Completion criteria

The routing/dispatch foundation is complete when:

- no normalized routing/dispatch contract uses optional fields to represent mutually exclusive states,
- arbitrary legacy route dictionaries exist only at parser boundaries,
- frontend system routing and app routing are distinct typed stages,
- backend routing produces the same normalized `DispatchRequest` family,
- route-vs-query precedence matches Webasyst 4.2.0 characterization tests,
- controller/action/actions resolution order matches `waFrontController::getController()` from 4.2.0,
- app-specific dispatch strategy override is injectable,
- FastAPI/Starlette request objects do not enter compatibility-core contracts,
- compatibility behavior is covered by unit/characterization/ASGI tests,
- `AGENTS.md` contains the nullable-state invariant and routing/dispatch ADRs.
