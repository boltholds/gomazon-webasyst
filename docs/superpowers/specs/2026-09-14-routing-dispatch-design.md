# Webasyst Routing & Dispatch Compatibility — Design Specification

Status: accepted design baseline
Date: 2026-09-14
Repository: `boltholds/gomazon-webasyst`

## 1. Goal

Implement Webasyst 4.2.0 routing and front-controller compatibility in Python without reproducing PHP global state, dynamic class loading, or nullable dictionary-shaped state throughout the new runtime.

Legacy route configuration is accepted only at a compatibility boundary. After parsing, the runtime operates on closed Pydantic variants.

The central invariant is:

> Nullable/optional fields must not encode mutually exclusive architectural states. Use discriminated unions and normalize legacy input at compatibility boundaries. `None` is allowed only when absence itself is a valid domain value.

This invariant is also recorded in `AGENTS.md` as ADR-014.

## 2. Sources of truth

Compatibility decisions use:

1. the supplied Webasyst Framework 4.2.0 source archive;
2. official Webasyst developer documentation at `https://developers.webasyst.com/docs`.

When current documentation and the supplied 4.2.0 source disagree, 4.2.0 source behavior wins unless a later ADR intentionally chooses newer behavior.

Relevant documentation:

- `https://developers.webasyst.com/docs/cookbook/basics/routing/`
- `https://developers.webasyst.com/docs/cookbook/backend-routing/`
- `https://developers.webasyst.com/docs/basics/naming-rules/`
- `https://developers.webasyst.com/docs/basics/`

Relevant source:

- `wa-system/routing/waRouting.class.php`
- `wa-system/controller/waFrontController.class.php`

### Dispatch-order discrepancy

Current naming-rules documentation describes `Controller -> Actions -> Action`. Webasyst 4.2.0 `waFrontController::getController()` and routing documentation use:

```text
Controller
-> Single Action
-> Multi Actions
-> optional default-module fallback when try_default is enabled
-> 404
```

The Python compatibility resolver preserves the 4.2.0 order.

## 3. Boundary rule: parse once

Legacy PHP route shapes may contain arbitrary keys such as `app`, `module`, `action`, `plugin`, `redirect`, `code`, `static_content`, flags, captures, and application-specific values.

They must not become internal contracts.

Bad model:

```python
class RouteRule(BaseModel):
    app: str | None = None
    module: str | None = None
    action: str | None = None
    plugin: str | None = None
    redirect: str | None = None
```

Required flow:

```text
legacy dict / shorthand string
          |
          v
LegacyRouteParser
          |
validation + normalization
          |
          v
closed discriminated-union rule variants
          |
          v
matcher / resolver / dispatcher
```

Only the parser/normalizer may reason about arbitrary legacy key combinations.

## 4. Separate request types

Frontend and backend routing are not represented by one object with an environment flag.

```python
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

Starlette/FastAPI request objects stay in presentation code.

## 5. Frontend routing is a typed two-stage pipeline

Webasyst frontend resolution is modeled as:

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

The system route selects a settlement/application. App routing resolves the remaining path into final dispatch.

A system settlement is never represented as a partially filled final dispatch object.

## 6. Route patterns

The first slice supports the relevant Webasyst 4.2.0 pattern forms:

- literal paths,
- `*` wildcards,
- `<name>` captures,
- `<name:regex>` captures,
- rule ordering,
- shorthand route values.

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

A compiled `re.Pattern` may be cached inside the matcher, but it is not a cross-layer contract.

## 7. Dynamic route data is allowed only when it is actually dynamic domain data

Webasyst routes may intentionally carry arbitrary application parameters. Their dynamic keys are a valid domain property and therefore are not modeled as dozens of optional fields.

Use a JSON-compatible value type:

```python
from pydantic import JsonValue

RouteData = dict[str, JsonValue]
```

Dispatch control fields (`module`, `action`, `plugin`) are removed from this generic data during normalization and represented by `DispatchSeed`/`DispatchRequest` variants instead.

## 8. Dispatch seed variants

A system route may preselect dispatch information before app routing. Webasyst 4.2.0 stores this in request params; Python represents it explicitly.

```python
class EmptySeed(BaseModel):
    kind: Literal["empty"] = "empty"


class ModuleSeed(BaseModel):
    kind: Literal["module"] = "module"
    module: str


class ActionSeed(BaseModel):
    kind: Literal["action"] = "action"
    module: str
    action: str


class PluginModuleSeed(BaseModel):
    kind: Literal["plugin_module"] = "plugin_module"
    plugin: str
    module: str


class PluginActionSeed(BaseModel):
    kind: Literal["plugin_action"] = "plugin_action"
    plugin: str
    module: str
    action: str


DispatchSeed = Annotated[
    EmptySeed
    | ModuleSeed
    | ActionSeed
    | PluginModuleSeed
    | PluginActionSeed,
    Field(discriminator="kind"),
]
```

There are no `module=None`, `action=None`, or `plugin=None` fields.

## 9. System routing outcomes

```python
class AppSettlement(BaseModel):
    kind: Literal["app"] = "app"
    app: str
    matched_prefix: str
    seed: DispatchSeed
    route_data: RouteData


class RedirectSettlement(BaseModel):
    kind: Literal["redirect"] = "redirect"
    location: str
    status_code: Literal[301, 302]


SettlementResolution = Annotated[
    AppSettlement | RedirectSettlement,
    Field(discriminator="kind"),
]
```

Static-content routes are outside this slice. When migrated, they get their own result variant rather than `static_content: str | None`.

System configuration is also normalized into closed rule variants:

```python
SystemRouteRule = Annotated[
    AppSettlementRule | RedirectRule,
    Field(discriminator="kind"),
]
```

## 10. Dispatch namespaces

Plugin dispatch is a different namespace, not a nullable field on an app request.

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

## 11. Final dispatch requests

Default dispatch and explicit-action dispatch have different behavior and are different types.

```python
class DefaultDispatch(BaseModel):
    kind: Literal["default"] = "default"
    namespace: DispatchNamespace
    module: str
    route_data: RouteData


class ActionDispatch(BaseModel):
    kind: Literal["action"] = "action"
    namespace: DispatchNamespace
    module: str
    action: str
    route_data: RouteData


DispatchRequest = Annotated[
    DefaultDispatch | ActionDispatch,
    Field(discriminator="kind"),
]
```

A final dispatch request is fully normalized. Frontend/backend defaults and all route/query precedence have already been applied.

## 12. App-route normalization

Legacy application routing may use shorthand such as:

```php
'rss/' => 'frontend/rss'
```

The parser converts shorthand and array forms into explicit app-route variants. The matcher never sees shorthand strings.

The app resolver receives `AppSettlement`, matches the remaining path, combines app-route controls with the explicit `DispatchSeed`, and emits one final `DispatchRequest`.

Dispatch control keys are never recovered by reading arbitrary `route_data`.

## 13. Matching semantics preserved in the first slice

Characterize and preserve:

- domain-specific routes with `default` fallback,
- domain aliases,
- route order,
- `temporarily_off` skipping,
- wildcard matching,
- named regex captures,
- first matching route wins during dispatch,
- URL decoding behavior relevant to matching,
- trailing-slash canonicalization to 301 when the slash version matches a non-catch-all rule,
- redirect routes default to 301 and use 302 only when configured,
- route-derived dispatch controls override query controls according to 4.2.0 behavior.

Excluded initially:

- `priority_settlement`,
- generated page routes,
- static-content serving.

## 14. Backend normalization

`waFrontController::getDispatchParams()` behavior is characterized directly from 4.2.0:

- backend query may provide `module`, `action`, `plugin`,
- module defaults to `backend`,
- routing controls override query controls,
- when routing supplies a module but no action, query action is still considered,
- plugin/module/action identifiers must match `^[a-z_][a-z0-9_]*$` case-insensitively.

The backend resolver performs this merge once and returns `DefaultDispatch` or `ActionDispatch`.

Invalid controls raise typed `InvalidDispatchParameter` mapped to HTTP 400.

Widgets are a separate slice and never appear as `widget: str | None` in these contracts.

## 15. Handler registry: preserve behavior, not PHP autoloading

Webasyst 4.2.0 generates PHP class names and calls `class_exists()`. Python will use an explicit injected registry.

Conceptually:

```python
registry.register_controller(key, handler)
registry.register_action(key, handler)
registry.register_actions(key, handler)
```

Registry keys must also use explicit default/action variants; do not encode action absence as `action=None`.

## 16. Handler target variants

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

A nullable `method` field is forbidden. Only multi-action targets carry an action method because it is genuinely part of that state.

## 17. Handler resolution order

Explicit action:

```text
{namespace}{module}{action}Controller
{namespace}{module}{action}Action
{namespace}{module}Actions::{action}Action
```

Default request:

```text
{namespace}{module}Controller
{namespace}{module}Action
{namespace}{module}Actions::defaultAction
```

If explicit-action resolution fails and legacy `try_default` is enabled, perform one second lookup using the corresponding default-request variant.

Then return typed `DispatchTargetNotFound` -> 404.

## 18. Front-controller overrides

Webasyst apps may override `factories.php['front_controller']`.

Python preserves the extension seam through DI:

```text
DispatchStrategyRegistry
    app id -> DispatchStrategy
```

The standard strategy uses the standard route/handler resolvers. An app-specific strategy may replace dispatch behavior for its app.

No global factory/service locator is introduced.

## 19. Errors and successful non-dispatch outcomes

Initial typed errors:

- `InvalidDispatchParameter` -> 400
- `RouteNotFound` -> 404
- `DispatchTargetNotFound` -> 404
- `PluginUnavailable` -> 404

Redirect is a successful routing outcome, not an exception.

Authorization remains a later auth/permissions slice. The routing core exposes a seam but does not implement Webasyst sessions/rights here.

## 20. Package boundaries

Target additions:

```text
src/gomazon_webasyst/
  contracts/
    routing.py
    dispatch.py

  application/ports/
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

Compatibility code may depend on contracts and application-owned ports. Application use cases must not import Webasyst compatibility modules.

## 21. Testing strategy

### Legacy parser tests

Feed representative Webasyst route arrays/shorthand strings and assert exact normalized variants. Malformed/ambiguous shapes fail here.

### Pattern tests

Cover literals, wildcard, `<name>`, `<name:regex>`, decoding, route order, aliases, and trailing slash.

### System/app resolver tests

Test stages independently. System resolution returns settlement variants, never partially populated dispatch objects.

Include system routes that seed module/action/plugin controls and prove they become `DispatchSeed`, not generic `route_data`.

### Backend normalization tests

Capture exact query-vs-routing precedence and identifier validation from `waFrontController::getDispatchParams()`.

### Handler resolver tests

Prove 4.2.0 order:

1. controller,
2. single action,
3. multi actions,
4. optional default fallback,
5. not found.

### ASGI compatibility tests

Prove redirect/error/dispatch transport translation without introducing FastAPI request objects into compatibility-core contracts.

### Source-backed characterization

When behavior is subtle or docs conflict with source, test/fixture documentation names the relevant 4.2.0 class/method.

## 22. Explicit non-goals

This slice does not implement:

- Webasyst auth/session/permission checks,
- CSRF,
- widgets,
- `priority_settlement`,
- generated page routes,
- static-content route serving,
- sitemap/captcha/payment special paths,
- PHP autoload/class discovery,
- plugin locale/lifecycle behavior,
- full `waRouting::getUrl()` parity.

These require later explicit variants/slices.

## 23. Completion criteria

The routing/dispatch foundation is complete when:

- normalized contracts do not use optional fields as state discriminators,
- arbitrary legacy dictionaries exist only at parser boundaries,
- dispatch controls are extracted into typed seed/request variants rather than hidden in generic route data,
- frontend system and app routing are distinct typed stages,
- backend routing emits the same final `DispatchRequest` family,
- route/query precedence matches 4.2.0 characterization tests,
- handler order matches `waFrontController::getController()` from 4.2.0,
- app-specific dispatch strategy override is injectable,
- Starlette/FastAPI request objects do not enter the compatibility core,
- behavior is covered by unit/characterization/ASGI tests,
- `AGENTS.md` contains the union-state invariant, source-precedence rule, and staged routing ADR.
