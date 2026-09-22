# Backend route catalog foundation — Design

Status: implemented
Date: 2026-09-22
Authoritative source: Webasyst Framework 4.2.0 release commit `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`

## Goal

Add the compatibility layer required to consume real bundled-app `routing.backend.php` files before migrating backend HTML/actions.

Team 2.3.4 is the first characterized application, but the loader/resolver is generic.

## Source behavior

`waFrontController::dispatch()` checks for `lib/config/routing.backend.php` only in backend environment.

The app backend route table runs only when both incoming query controls are PHP-empty:

- module;
- plugin.

The matched route writes routing params. `getDispatchParams()` then reads query controls and lets routing params override them. Existing Python `BackendRouteResolver` already models this normalization, including the special case where a route supplies module but no action and query action survives.

When a backend route file is active but no rule produces a module, Webasyst throws front-controller dispatch miss. It does not silently select the normal backend module.

When no backend route file exists, ordinary backend default dispatch remains valid.

## Loading boundary

`FilesystemBackendRouteCatalog` uses:

```text
LegacyApplicationPathPolicy
-> parse_php_return_value()
-> PHP array normalization
-> parse_app_routes()
```

No PHP interpreter, subprocess, eval/import execution or class-name discovery is used.

Results are explicit:

```text
BackendRoutesMissing
BackendRoutesLoaded(routes)
```

The path policy prevents app-id filesystem escapes and supports ordinary apps plus the special Webasyst system-app path.

## Match boundary

`BackendAppRouteResolver` is a separate stage from `BackendRouteResolver`.

Input:

```text
backend path + ordered AppDispatchRule tuple
```

Output:

```text
BackendAppRouteMatched(seed, route_data)
BackendAppRouteNotMatched
```

Captures that are dispatch controls are folded into the typed seed. Other captures become route data. Explicit route data overwrites same-name captures, matching app-route behavior.

## Compatibility service orchestration

`LegacyCompatibilityService.resolve_backend()` applies backend app routes only when:

1. the caller did not already provide an explicit dispatch seed;
2. the app exists in the supplied backend route table;
3. query module and plugin are PHP-empty (`""`, absent, or `"0"`).

On a match, the produced seed/data is passed into the existing `BackendRouteResolver`.

On an active-table miss, `RouteNotFound` is raised.

When the app has no route-table entry, behavior stays exactly as before.

## Installed application composition

`create_installed_backend_route_table()` snapshots the canonical `InstalledApplicationCatalog`, checks only those app ids through the filesystem catalog, drops explicit missing-route results and returns an immutable mapping.

The builder is intentionally separate from `ApplicationRuntimeModule` because routing configuration is declarative compatibility metadata, while runtime modules declare executable Python API/dispatch/event handlers.

## Team acceptance surface

Team 2.3.4 source has 21 ordered backend rules including:

- profile routes by login and id;
- calendar routes;
- group manage/access routes;
- online/settings/plugins/welcome/invited/inactive/no-access/search routes;
- explicit calendar external authorize route carrying `authorize_end=1`;
- empty path -> `users/`.

Representative rules are parsed/matched in unit and ASGI tests, while the complete route inventory is source-characterized.

## Security

Backend route loading:

- reuses the contained application path policy;
- accepts only declarative PHP return values;
- never executes PHP;
- never dynamically imports Python;
- does not register a handler because a route exists.

A route can resolve only as far as the existing explicit dispatch registry permits.

## Non-goals

This slice does not:

- mount the legacy catch-all in production;
- implement Team Smarty/backend actions;
- register placeholder/fake handlers for Team route targets;
- migrate `webasyst.backend_dispatch_miss`;
- migrate personal-profile redirect side effects;
- perform backend session/auth/rights checks for the legacy catch-all.

Those belong to later backend execution/rendering slices.

## Acceptance

Complete when:

- Team backend route inventory and front-controller gate are source-pinned;
- filesystem loading is restricted and path-contained;
- missing route file is explicit;
- route order/captures/extra data are preserved;
- query module/plugin bypass route matching;
- matched route feeds existing backend query precedence;
- active table miss does not fall back to backend;
- installed-app composition returns immutable route mapping;
- ASGI compatibility test proves backend path route resolution;
- legacy catch-all remains unmounted in production;
- full CI is green.
