# Backend route catalog foundation — Implementation Plan

Status: implemented
Date: 2026-09-22

- [x] Pin Webasyst 4.2.0 backend front-controller routing gate.
- [x] Pin Team 2.3.4 `routing.backend.php` route inventory.
- [x] Extend contained legacy application path policy to backend route config.
- [x] Reuse restricted declarative PHP return-value parser.
- [x] Normalize PHP arrays without executing PHP.
- [x] Add explicit missing/loaded route-catalog states.
- [x] Parse loaded configuration through existing `parse_app_routes()`.
- [x] Add separate `BackendAppRouteResolver`.
- [x] Preserve ordered route matching and capture/explicit-data precedence.
- [x] Keep `BackendRouteResolver` as query/seed normalization stage.
- [x] Skip backend app routes for non-empty query module/plugin.
- [x] Preserve query action when route provides module only.
- [x] Preserve route action/module precedence over query.
- [x] Map active route-table miss to typed `RouteNotFound`.
- [x] Keep no-route-file behavior on ordinary backend default path.
- [x] Build immutable route mapping from canonical installed-app snapshot.
- [x] Add no-eval/subprocess/dynamic-import architecture guard.
- [x] Prove backend path dispatch through ASGI compatibility router.
- [x] Keep production catch-all unmounted.
- [x] Record architecture decision.
- [x] Run full CI.

## Verification record

Final code head before documentation commit: `3ee219496753c1e4a0f96428085a0dc16af39d5c`.

GitHub Actions completed successfully on that head:

- source-tree compile passed;
- **911 passed, 11 warnings**;
- restricted backend route filesystem loader passed;
- application path containment passed;
- typed match/miss resolver passed;
- query module bypass passed;
- route/query precedence passed;
- active-table miss behavior passed;
- immutable canonical installed-app table composition passed;
- ASGI backend path route dispatch passed;
- architecture no-execution guard passed.
