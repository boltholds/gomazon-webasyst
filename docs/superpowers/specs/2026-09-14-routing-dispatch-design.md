# Webasyst Routing & Dispatch Compatibility — Design Specification

Status: accepted, implementation-aligned
Date: 2026-09-14
Repository: `boltholds/gomazon-webasyst`

## Goal

Implement Webasyst 4.2.0 routing/front-controller compatibility in Python while keeping PHP-shaped dynamic state at the compatibility boundary. After parsing, routing and dispatch operate on closed Pydantic variants.

The governing invariant is:

> Nullable/optional fields must not encode mutually exclusive architectural states. Use discriminated unions and normalize legacy input at compatibility boundaries. `None` is allowed only when absence itself is a valid domain value.

## Sources of truth

Compatibility decisions use both the supplied Webasyst Framework 4.2.0 source and official documentation at `https://developers.webasyst.com/docs`.

Relevant source:

- `wa-system/routing/waRouting.class.php`
- `wa-system/controller/waFrontController.class.php`
- `wa-system/controller/waActions.class.php`

Relevant docs:

- `https://developers.webasyst.com/docs/cookbook/basics/routing/`
- `https://developers.webasyst.com/docs/cookbook/backend-routing/`
- `https://developers.webasyst.com/docs/basics/naming-rules/`
- `https://developers.webasyst.com/docs/basics/`

If current docs conflict with 4.2.0 source, 4.2.0 source wins unless a later ADR explicitly chooses newer behavior.

Known discrepancy: naming-rules documentation describes `Controller -> Actions -> Action`; 4.2.0 `waFrontController::getController()` resolves `Controller -> Single Action -> Multi Actions`. The migration preserves 4.2.0.

## Boundary model

Legacy PHP route dictionaries and shorthand strings are accepted only by `LegacyRouteParser`:

```text
legacy dict / shorthand string
          -> LegacyRouteParser
          -> closed typed route variants
          -> matcher/resolvers
          -> fully normalized dispatch
```

`dict[str, Any]` does not cross beyond parsing. Dynamic application route values are represented separately as JSON-compatible `RouteData`.

## Request types

Frontend and backend are distinct contracts:

```text
FrontendRouteRequest(domain, path, query)
BackendRouteRequest(app, path, query)
```

No `environment` flag is used to switch unrelated semantics inside one DTO. FastAPI/Starlette request objects stay in presentation.

## Route patterns

`RoutePattern` stores the legacy source, normalized regex source, and named captures. The matcher supports the 4.2.0 forms used by this slice:

- literals;
- `*` / repeated wildcard;
- `<name>`;
- `<name:regex>`;
- case-insensitive full-string matching;
- the legacy escaping behavior for spaces, `.`, `(`, and `!`.

Compiled `re.Pattern` objects remain implementation details.

## Dispatch seed is a closed state machine

A system/app route may contain only some dispatch-control fields. Missing control fields are semantically important because `waRouting` treats an explicitly supplied `module` differently from a module that is still absent.

Therefore `DispatchSeed` has explicit variants:

```text
EmptySeed
ModuleSeed
ActionOnlySeed
ActionSeed
PluginSeed
PluginActionOnlySeed
PluginModuleSeed
PluginActionSeed
```

This preserves all meaningful combinations of `module`, `action`, and `plugin` without `None`-driven state.

## Frontend two-stage routing

```text
FrontendRouteRequest
  -> SystemRouteResolver
  -> SettlementResolution
  -> AppRouteResolver
  -> ResolvedDispatch
```

`SettlementResolution` is:

```text
AppSettlement | RedirectSettlement
```

`AppSettlement` contains:

- app id;
- `matched_prefix`;
- `remaining_path` for the second routing stage;
- normalized `DispatchSeed`;
- `AppRouteConstraint`;
- dynamic `RouteData`.

`AppRouteConstraint` is itself a union:

```text
AnyAppRouteConstraint | ModuleRouteConstraint
```

The constraint preserves a subtle 4.2.0 rule: if the raw system settlement explicitly contains `module`, app routes without that exact explicit module are skipped. A module obtained later from URL capture must not accidentally create this restriction.

### System resolver compatibility

The resolver preserves:

- exact domain with `default` fallback;
- aliases;
- route order;
- `temporarily_off` skipping;
- disabled redirect skipping;
- named/wildcard captures;
- explicit route values overriding captured values;
- redirect wildcard interpolation;
- query-string preservation for wildcard redirects;
- valid UTF-8 URL decoding before matching;
- Webasyst trailing-slash retry/canonical 301 behavior for wildcard/no-match cases.

`priority_settlement` and static-content routes are rejected by the first parser rather than represented incorrectly.

### App resolver compatibility

App routing reuses accumulated settlement params. Precedence matches the `waRequest::param` side effects of `dispatchRoutes()`:

1. parent settlement params already exist;
2. app-route captures fill only missing params;
3. explicit app-route fields override everything.

If no app route matches, this is **not a routing 404**. Webasyst 4.2.0 ignores the null result of the second `dispatchRoutes()` and front-controller defaults still apply. The Python resolver therefore produces dispatch from the settlement seed, with frontend module default `frontend`.

## Final dispatch data

Control state and arbitrary route data remain separate:

```text
ResolvedDispatch
  request: DefaultDispatch | ActionDispatch
  route_data: RouteData
```

Namespaces are:

```text
AppNamespace | PluginNamespace
```

No final normalized request contains nullable `module`, `action`, or `plugin` fields.

## Backend normalization

`BackendRouteResolver` characterizes `waFrontController::getDispatchParams()`:

- query may provide module/action/plugin;
- module defaults to `backend` when not supplied;
- route seed values override query values;
- if route supplies module but no action, query action survives;
- action-only/plugin-only seeds preserve the other query controls;
- non-empty dispatch identifiers must match `^[a-z_][a-z0-9_]*$` case-insensitively;
- invalid values raise typed `InvalidDispatchParameter` mapped to HTTP 400.

Backend result is also `ResolvedDispatch`.

## Handler registry and resolution

PHP dynamic class discovery is not reproduced. An application-owned `DispatchRegistry` protocol and explicit registry map typed keys to opaque handler IDs.

Handler keys are also closed types:

```text
ModuleHandlerKey
ActionHandlerKey
```

Resolver order for explicit action:

```text
Controller(ActionHandlerKey)
-> Single Action(ActionHandlerKey)
-> Multi Actions(ModuleHandlerKey, action_method=<action>)
-> optional default retry only when caller explicitly requests try_default
-> 404
```

Default dispatch checks controller/action/multi-actions by module key. `waActions::run(null)` maps to `defaultAction`, so `MultiActionTarget` always has a concrete `action_method`, using `default` for default dispatch.

Plugin availability is explicit in the registry. Missing/disabled plugins produce typed `PluginUnavailable`.

## Front-controller override seam

Webasyst `factories.php['front_controller']` is represented through DI:

```text
DispatchStrategyRegistry
  default DispatchStrategy
  optional app-id overrides
```

Plugin requests use the strategy of their owning app. No global factory/service locator is introduced.

## Compatibility service outcome

The orchestration service returns another discriminated union rather than an implicit tuple/nullable result:

```text
LegacyDispatchOutcome = RedirectSettlement | HandlerDispatchOutcome
```

`HandlerDispatchOutcome` contains both `ResolvedDispatch` and `DispatchTarget`.

## Presentation boundary

`create_legacy_compatibility_router()` is a router factory. It translates ASGI request data to typed frontend/backend request contracts, calls the compatibility service, maps typed errors to HTTP status codes, and invokes an injected handler by opaque handler ID.

The router is **not mounted as a production catch-all in `main.py` in this slice**. This prevents unproven compatibility behavior from shadowing native Python APIs.

## Errors

Initial typed errors:

- `InvalidLegacyRoute` — unsupported/malformed legacy config;
- `InvalidDispatchParameter` — HTTP 400;
- `RouteNotFound` — HTTP 404;
- `DispatchTargetNotFound` — HTTP 404;
- `PluginUnavailable` — HTTP 404.

Redirects are successful outcomes, not exceptions.

## Non-goals

This slice does not implement auth/session/permission checks, CSRF, widgets, `priority_settlement`, generated page routes, static-content serving, PHP autoloading, plugin lifecycle/locale initialization, or `waRouting::getUrl` parity.

## Completion criteria

The slice is complete when:

- mutually exclusive states use closed unions;
- legacy dictionaries terminate at parser boundaries;
- seed variants preserve control-field presence/absence semantics;
- system/app/backend routing are distinct typed stages;
- app settlement carries the second-stage remaining path explicitly;
- app-route miss falls through to front-controller defaults rather than false 404;
- route data survives separately from dispatch controls;
- handler resolution matches 4.2.0 order;
- app-specific dispatch strategy is injectable;
- ASGI tests prove redirects, frontend dispatch, backend dispatch, 400 and 404 translation;
- production `main.py` remains free of the legacy catch-all;
- full tests and architecture guard pass.
