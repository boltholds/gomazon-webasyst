# Webasyst 4.2.0 backend route catalog — Characterization

Status: source-pinned
Date: 2026-09-22
Authoritative release commit: `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`

## Sources

- `wa-system/controller/waFrontController.class.php::dispatch()`
- `wa-system/controller/waFrontController.class.php::getDispatchParams()`
- `wa-system/routing/waRouting.class.php::dispatchRoutes()`
- `wa-apps/team/lib/config/routing.backend.php`

## Backend routing gate

For a backend request Webasyst checks whether the active app has `lib/config/routing.backend.php`.

That route file is dispatched only when both query controls are PHP-empty:

- module;
- plugin.

When query module or plugin is non-empty, the app backend route table is skipped and normal backend query dispatch proceeds.

## Match and merge semantics

Backend app routes use the same route pattern/capture semantics as other app routes.

A matched route writes routing params. Later `getDispatchParams()` reads query controls and then lets routing params override them.

The existing Python `BackendRouteResolver` already models the second part:

- route module/action/plugin override query controls;
- route module with no action leaves query action available;
- invalid final dispatch identifiers are rejected.

Therefore backend path matching is a separate pre-stage that produces only a typed route seed and route data.

## Route miss

When a backend route file exists and is active for the request, Webasyst calls routing dispatch and then requires a routing `module` param.

If no route matched and no module was produced, front-controller dispatch-miss is raised. It does not silently fall back to the ordinary backend module.

When no backend route file exists, ordinary backend default normalization remains valid.

## Declarative loading

`routing.backend.php` in the characterized Team application is a pure top-level return array. It can therefore be read by the existing restricted declarative PHP parser. No PHP execution, include, variable interpolation or dynamic class loading is required.

The Team table has 21 ordered routes. The final empty-string route maps the app root to `users/`. The calendar authorization route is an explicit mapping carrying extra route data `authorize_end=1`.

## Architecture consequence

Backend route configuration is declarative compatibility metadata, not an executable runtime handler. It is loaded into a compatibility-owned immutable per-app route catalog.

Executable controller/action availability remains in the existing explicit dispatch registry. Loading a route must never imply that the target Python handler exists.

The production legacy catch-all remains unmounted until backend handlers/rendering are deliberately migrated.
