# Routing & Dispatch Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build typed Webasyst 4.2.0 routing/front-controller compatibility without nullable state bags or PHP dynamic class discovery.

**Architecture:** Parse legacy config once, then operate on Pydantic discriminated unions. Frontend system/app routing and backend normalization produce `ResolvedDispatch`; explicit registry/strategy layers resolve handlers in 4.2.0 order. The ASGI adapter is factory-only and is not mounted in production `main.py` yet.

**Tech Stack:** Python 3.12+, Pydantic v2, FastAPI/Starlette at presentation boundary, pytest.

**Spec:** `docs/superpowers/specs/2026-09-14-routing-dispatch-design.md`

## Global Constraints

- Preserve ADR-014 discriminated-union rule.
- Webasyst 4.2.0 source wins over conflicting current docs.
- No arbitrary route dictionaries beyond parser boundaries.
- No FastAPI/Starlette types in contracts/application/compatibility core.
- Existing native contact endpoints must remain untouched.

---

### Task 1: Closed routing/dispatch contracts

- [x] Add frontend/backend request contracts and route-pattern contracts.
- [x] Add eight `DispatchSeed` variants covering all meaningful `module/action/plugin` presence combinations.
- [x] Add `AppRouteConstraint` variants.
- [x] Add `AppSettlement` with `matched_prefix` and `remaining_path`.
- [x] Add namespace, dispatch request, handler key, target, `ResolvedDispatch`, and final compatibility outcome unions.
- [x] Verify contract and architecture-boundary tests.

### Task 2: Route pattern engine

- [x] Characterize literals, wildcards, `<name>`, `<name:regex>`, case-insensitivity, dot escaping, and legacy parenthesis behavior.
- [x] Implement compiler and matcher returning named captures plus wildcard substring.
- [x] Verify unit tests.

### Task 3: Legacy route parser

- [x] Characterize `waRouting::formatRoutes()` system/app shorthand differences.
- [x] Preserve route order and domain aliases.
- [x] Normalize redirect rules separately from app settlement rules.
- [x] Remove control fields from dynamic route data.
- [x] Reject unsupported `priority_settlement`/static content in this slice.
- [x] Verify parser + source-backed characterization tests.

### Task 4: Frontend system/app resolvers

- [x] Implement exact/default/alias system route selection.
- [x] Preserve `temporarily_off`, disabled redirects, capture/explicit precedence, UTF-8 decoding, wildcard redirects, query preservation, and trailing-slash 301 behavior.
- [x] Preserve explicit-module app-route restriction using `AppRouteConstraint`.
- [x] Carry `remaining_path` into the app stage.
- [x] Merge parent params, app captures, then explicit app route data in legacy precedence.
- [x] On app-route miss, dispatch from settlement/default frontend state rather than raising false routing 404.
- [x] Verify system/app resolver tests.

### Task 5: Backend normalization

- [x] Characterize `waFrontController::getDispatchParams()` query/default/route precedence.
- [x] Preserve action-only/plugin-only route seed semantics.
- [x] Validate non-empty identifiers with the legacy regex.
- [x] Keep route data separate from dispatch controls.
- [x] Verify backend resolver tests.

### Task 6: Explicit handler registry + 4.2.0 resolver

- [x] Add application-owned `DispatchRegistry` protocol.
- [x] Add explicit in-memory registry with plugin availability.
- [x] Resolve Controller -> Single Action -> Multi Actions.
- [x] Support explicit `try_default` retry without enabling it for normal dispatch.
- [x] Map default multi-actions to concrete `default` action method.
- [x] Verify registry/resolver tests.

### Task 7: Per-app dispatch strategy override

- [x] Add `DispatchStrategy` protocol and registry.
- [x] Select override by owning app for both app and plugin namespaces.
- [x] Verify strategy tests.

### Task 8: Compatibility service + ASGI adapter

- [x] Add core orchestration returning `RedirectSettlement | HandlerDispatchOutcome`.
- [x] Add backend `/webasyst/{app}/...` and frontend catch-all routes in a router factory.
- [x] Map invalid dispatch -> 400 and missing route/target/plugin -> 404.
- [x] Invoke injected handlers by opaque handler ID.
- [x] Keep the router unmounted from production `main.py`.
- [x] Verify ASGI integration tests.

### Final verification

- [x] `python -m pytest -q` locally: 86 passed, 3 driver-dependent foundation skips.
- [x] `python -m compileall -q src`: exit 0.
- [ ] GitHub Actions Python 3.12 full suite after branch synchronization.
