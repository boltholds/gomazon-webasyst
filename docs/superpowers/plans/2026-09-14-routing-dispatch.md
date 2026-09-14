# Routing & Dispatch Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a typed Webasyst 4.2.0 routing/front-controller compatibility pipeline with discriminated Pydantic unions, legacy route normalization, deterministic route matching, backend parameter normalization, and explicit handler dispatch.

**Architecture:** Arbitrary Webasyst route arrays/shorthand strings terminate at `LegacyRouteParser`. Downstream code consumes closed Pydantic variants only. Frontend routing is staged (`system -> settlement -> app -> dispatch`), backend routing has a separate normalizer, and handler discovery uses an injectable registry preserving Webasyst 4.2.0 `Controller -> Action -> Actions -> optional default fallback` semantics.

**Tech Stack:** Python 3.12+, Pydantic v2, FastAPI/Starlette only at presentation boundary, pytest.

**Spec:** `docs/superpowers/specs/2026-09-14-routing-dispatch-design.md`

## Global Constraints

- Preserve `AGENTS.md` ADR-014: mutually exclusive states use discriminated unions, not nullable field bags.
- Preserve ADR-015: Webasyst 4.2.0 source wins over conflicting current documentation.
- Preserve ADR-016: frontend system routing, app routing, backend normalization, and dispatch are distinct typed stages.
- `dict[str, Any]` and shorthand strings may exist only at the legacy parser boundary.
- FastAPI/Starlette request objects must not enter routing/dispatch contracts or compatibility core.
- `module`, `action`, and `plugin` must be normalized before final `DispatchRequest` construction.
- Route list order is significant; first eligible matching rule wins.
- First slice excludes widgets, auth/permissions, `priority_settlement`, generated page routes, static-content serving, and `waRouting::getUrl` parity.

---

## File Map

```text
src/gomazon_webasyst/
  contracts/
    routing.py
    dispatch.py
  application/ports/
    dispatch_registry.py
  compatibility/
    __init__.py
    webasyst/
      __init__.py
      routing/
        __init__.py
        errors.py
        patterns.py
        legacy_parser.py
        system_resolver.py
        app_resolver.py
        backend_resolver.py
      dispatch/
        __init__.py
        errors.py
        keys.py
        registry.py
        resolver.py
        strategies.py
  presentation/http/
    legacy_dispatch.py

tests/
  unit/
    test_routing_contracts.py
    test_route_patterns.py
    test_legacy_route_parser.py
    test_system_route_resolver.py
    test_app_route_resolver.py
    test_backend_route_resolver.py
    test_dispatch_registry.py
    test_dispatch_resolver.py
    test_dispatch_strategies.py
  compatibility/
    test_routing_characterization.py
  integration/
    test_legacy_dispatch_http.py
```

---

### Task 1: Define closed Pydantic routing and dispatch contracts

**Files:**
- Create: `src/gomazon_webasyst/contracts/routing.py`
- Create: `src/gomazon_webasyst/contracts/dispatch.py`
- Test: `tests/unit/test_routing_contracts.py`

**Interfaces:**
- Produces `FrontendRouteRequest`, `BackendRouteRequest`, `RoutePattern`, `RouteData`.
- Produces `DispatchSeed` variants: `EmptySeed`, `ModuleSeed`, `ActionSeed`, `PluginModuleSeed`, `PluginActionSeed`.
- Produces `SettlementResolution`: `AppSettlement | RedirectSettlement`.
- Produces `DispatchNamespace`: `AppNamespace | PluginNamespace`.
- Produces `DispatchRequest`: `DefaultDispatch | ActionDispatch`.
- Produces `DispatchTarget`: `ControllerTarget | SingleActionTarget | MultiActionTarget`.

- [ ] **Step 1: Write failing contract tests**

Create `tests/unit/test_routing_contracts.py`:

```python
import pytest
from pydantic import TypeAdapter, ValidationError

from gomazon_webasyst.contracts.dispatch import (
    ActionDispatch,
    AppNamespace,
    DispatchRequest,
    PluginNamespace,
)
from gomazon_webasyst.contracts.routing import (
    AppSettlement,
    DispatchSeed,
    RedirectSettlement,
    SettlementResolution,
)


def test_dispatch_request_is_discriminated_union() -> None:
    adapter = TypeAdapter(DispatchRequest)
    value = adapter.validate_python({
        "kind": "action",
        "namespace": {"kind": "app", "app": "blog"},
        "module": "frontend",
        "action": "post",
    })
    assert isinstance(value, ActionDispatch)
    assert isinstance(value.namespace, AppNamespace)


def test_plugin_namespace_requires_plugin() -> None:
    with pytest.raises(ValidationError):
        PluginNamespace(kind="plugin", app="shop")


def test_settlement_variants_do_not_share_nullable_control_fields() -> None:
    adapter = TypeAdapter(SettlementResolution)
    redirect = adapter.validate_python({
        "kind": "redirect",
        "location": "/new/",
        "status_code": 301,
    })
    assert isinstance(redirect, RedirectSettlement)
    assert not hasattr(redirect, "app")


def test_dispatch_seed_rejects_partial_action_state() -> None:
    adapter = TypeAdapter(DispatchSeed)
    with pytest.raises(ValidationError):
        adapter.validate_python({"kind": "action", "module": "frontend"})
```

Run:

```bash
python -m pytest tests/unit/test_routing_contracts.py -v
```

Expected: FAIL because the routing/dispatch contract modules do not exist.

- [ ] **Step 2: Implement routing contracts**

Create `src/gomazon_webasyst/contracts/routing.py` with frozen, `extra="forbid"` Pydantic models and these exact public types:

```python
RouteData = dict[str, JsonValue]
FrontendRouteRequest(domain: str, path: str, query: dict[str, str])
BackendRouteRequest(app: str, path: str, query: dict[str, str])
RouteCapture(name: str, regex: str)
RoutePattern(source: str, regex_source: str, captures: tuple[RouteCapture, ...])
EmptySeed(kind="empty")
ModuleSeed(kind="module", module: str)
ActionSeed(kind="action", module: str, action: str)
PluginModuleSeed(kind="plugin_module", plugin: str, module: str)
PluginActionSeed(kind="plugin_action", plugin: str, module: str, action: str)
DispatchSeed = Annotated[... five variants ..., Field(discriminator="kind")]
AppSettlement(kind="app", app: str, matched_prefix: str, seed: DispatchSeed, route_data: RouteData)
RedirectSettlement(kind="redirect", location: str, status_code: Literal[301, 302])
SettlementResolution = Annotated[AppSettlement | RedirectSettlement, Field(discriminator="kind")]
```

Use `Field(default_factory=dict)` only for genuinely empty dynamic dictionaries; do not use nullable control fields.

- [ ] **Step 3: Implement dispatch contracts**

Create `src/gomazon_webasyst/contracts/dispatch.py`:

```python
class AppNamespace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["app"] = "app"
    app: str

class PluginNamespace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["plugin"] = "plugin"
    app: str
    plugin: str

DispatchNamespace = Annotated[AppNamespace | PluginNamespace, Field(discriminator="kind")]

class DefaultDispatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["default"] = "default"
    namespace: DispatchNamespace
    module: str

class ActionDispatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["action"] = "action"
    namespace: DispatchNamespace
    module: str
    action: str

DispatchRequest = Annotated[DefaultDispatch | ActionDispatch, Field(discriminator="kind")]
```

Add frozen `ControllerTarget`, `SingleActionTarget`, and `MultiActionTarget(action_method: str)` and expose `DispatchTarget` as a discriminated union.

Run:

```bash
python -m pytest tests/unit/test_routing_contracts.py tests/architecture/test_dependency_boundaries.py -v
```

Expected: PASS.

---

### Task 2: Implement Webasyst-compatible route pattern compiler/matcher

**Files:**
- Create: `src/gomazon_webasyst/compatibility/__init__.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/__init__.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/routing/__init__.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/routing/patterns.py`
- Test: `tests/unit/test_route_patterns.py`

**Interfaces:**
- Produces `compile_route_pattern(source: str) -> RoutePattern`.
- Produces `match_route(pattern: RoutePattern, path: str) -> RouteMatch | None`, where `RouteMatch` is a private compatibility dataclass/model containing captures and wildcard capture.

- [ ] **Step 1: Write failing characterization tests**

```python
from gomazon_webasyst.compatibility.webasyst.routing.patterns import compile_route_pattern, match_route


def test_literal_and_named_capture() -> None:
    pattern = compile_route_pattern("post/<id:\\d+>/")
    match = match_route(pattern, "post/42/")
    assert match is not None
    assert match.captures == {"id": "42"}


def test_default_capture_is_non_greedy() -> None:
    pattern = compile_route_pattern("tag/<slug>/")
    assert match_route(pattern, "tag/a-b/").captures == {"slug": "a-b"}


def test_wildcard_matches_remaining_path() -> None:
    pattern = compile_route_pattern("files/*")
    match = match_route(pattern, "files/a/b.txt")
    assert match is not None
    assert match.wildcard == "a/b.txt"


def test_match_is_case_insensitive_like_php_ui_regex() -> None:
    pattern = compile_route_pattern("Blog/<slug>/")
    assert match_route(pattern, "blog/Hello/") is not None
```

Run and verify RED.

- [ ] **Step 2: Implement compiler**

Mirror the relevant 4.2.0 `waRouting::dispatchRoutes()` transformations:

```text
space -> \s
. -> \.
( -> (?:
! -> \!
* or ** -> non-greedy wildcard
<name> -> named capture using `.*?`
<name:regex> -> named capture using the provided regex
full-string match, case-insensitive
```

Store the compiled source string in `RoutePattern.regex_source`; actual `re.Pattern` is an internal cache/detail.

- [ ] **Step 3: Implement matcher and wildcard extraction**

`match_route()` must return captured placeholder values and the first wildcard substring needed by redirect interpolation. URL decoding belongs to the resolver/request normalization layer, not this function.

Run:

```bash
python -m pytest tests/unit/test_route_patterns.py -v
```

Expected: PASS.

---

### Task 3: Parse and normalize legacy system/app routes once

**Files:**
- Create: `src/gomazon_webasyst/compatibility/webasyst/routing/errors.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/routing/legacy_parser.py`
- Test: `tests/unit/test_legacy_route_parser.py`
- Test: `tests/compatibility/test_routing_characterization.py`

**Interfaces:**
- Produces typed `SystemRouteTable` with aliases and ordered rules per domain.
- Produces typed ordered `AppRouteRule` sequence.
- Produces `InvalidLegacyRoute` for malformed/unsupported shapes.

- [ ] **Step 1: Write parser tests for `formatRoutes()` semantics**

Tests must cover these source-backed cases:

```python
def test_system_shorthand_maps_first_segment_to_app_and_second_to_module():
    raw = {"example.com": {"blog/*": "blog/frontend"}}
    table = parse_system_routes(raw)
    rule = table.routes["example.com"][0]
    assert rule.app == "blog"
    assert rule.seed.kind == "module"
    assert rule.seed.module == "frontend"


def test_app_shorthand_maps_first_segment_to_module_and_second_to_action():
    rules = parse_app_routes("blog", {"rss/": "frontend/rss"})
    rule = rules[0]
    assert rule.dispatch.kind == "action"
    assert rule.dispatch.module == "frontend"
    assert rule.dispatch.action == "rss"


def test_domain_alias_points_to_existing_domain_rules():
    table = parse_system_routes({
        "example.com": [{"url": "*", "app": "site"}],
        "www.example.com": "example.com",
    })
    assert table.aliases["www.example.com"] == "example.com"
```

Also test that `redirect`, `code=302`, `temporarily_off`, explicit `plugin/module/action`, and arbitrary route data normalize to closed variants rather than optional control fields.

- [ ] **Step 2: Implement parser rule variants local to compatibility layer**

Use private/internal Pydantic models such as `AppSettlementRule`, `RedirectRule`, `AppDefaultRule`, and `AppActionRule`. Each must carry a compiled `RoutePattern` and only fields meaningful to that variant.

`parse_system_routes(raw)` accepts mapping/list shapes equivalent to PHP routing config and preserves iteration order.

`parse_app_routes(app, raw)` injects the app namespace and normalizes shorthand exactly as `waRouting::formatRoutes($routes, $app_id)` does.

Unsupported `static_content` and `priority_settlement` rules raise `InvalidLegacyRoute` in this first slice rather than being silently misrepresented.

- [ ] **Step 3: Add source-backed characterization names/comments**

`tests/compatibility/test_routing_characterization.py` should name `waRouting::formatRoutes` and `waRouting::dispatchRoutes` in test docstrings and assert route flags/ordering without copying PHP implementation structure.

Run parser + characterization tests; expected PASS.

---

### Task 4: Implement frontend system and app resolvers

**Files:**
- Create: `src/gomazon_webasyst/compatibility/webasyst/routing/system_resolver.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/routing/app_resolver.py`
- Test: `tests/unit/test_system_route_resolver.py`
- Test: `tests/unit/test_app_route_resolver.py`

**Interfaces:**
- `SystemRouteResolver.resolve(request: FrontendRouteRequest) -> SettlementResolution`.
- `AppRouteResolver.resolve(settlement: AppSettlement, path: str, rules: Sequence[AppRouteRule]) -> DispatchRequest`.
- Produces typed `RouteNotFound`.

- [ ] **Step 1: System resolver RED tests**

Cover:

- exact domain before `default`;
- alias resolution before route lookup;
- `temporarily_off` skipped;
- first matching enabled rule wins;
- captures become route data only if not replaced by explicit route data;
- explicit rule values win over captured values as in `dispatchRoutes()`;
- redirect wildcard interpolation preserves original query string;
- redirect defaults 301, explicit 302 preserved;
- UTF-8 URL decoding before matching;
- trailing-slash retry yields 301 only when slash form resolves to a more specific route than an existing `*` match.

- [ ] **Step 2: Implement system resolver**

Resolve domain table, match ordered rules, construct either `AppSettlement` or `RedirectSettlement`. Do not mutate process-global state.

For trailing slash behavior, perform the second match only when 4.2.0 would: no match, or current match is `url == "*"`, path non-empty, no apparent dot in final 5 chars, and no trailing slash. Redirect only if second result is non-wildcard or no first result.

- [ ] **Step 3: App resolver RED tests**

Cover:

- settlement `EmptySeed` + app action route;
- parent `ModuleSeed` restricts candidate app routes to the same module, matching 4.2.0 `dispatchRoutes()` behavior;
- settlement `ActionSeed` can result directly without nullable fields when app-route matching leaves it final;
- app route capture data does not become dispatch-control data accidentally;
- first matching app route wins;
- missing app route raises `RouteNotFound`.

- [ ] **Step 4: Implement app resolver**

Merge seed and selected app rule into a final `DefaultDispatch`/`ActionDispatch`. Namespace is `AppNamespace` or `PluginNamespace` based on seed/rule variant. All defaults must be resolved before return.

Run both resolver test files; expected PASS.

---

### Task 5: Implement backend dispatch normalization from query + route data

**Files:**
- Create: `src/gomazon_webasyst/compatibility/webasyst/routing/backend_resolver.py`
- Test: `tests/unit/test_backend_route_resolver.py`

**Interfaces:**
- `BackendRouteResolver.resolve(request: BackendRouteRequest, seed: DispatchSeed = EmptySeed()) -> DispatchRequest`.
- Produces `InvalidDispatchParameter` for names outside `^[a-z_][a-z0-9_]*$` case-insensitively.

- [ ] **Step 1: Write tests directly from `waFrontController::getDispatchParams()`**

```python
def test_backend_module_defaults_to_backend():
    result = resolver.resolve(BackendRouteRequest(app="team", path="", query={}))
    assert result.kind == "default"
    assert result.module == "backend"


def test_route_seed_overrides_query_module_and_action():
    result = resolver.resolve(
        BackendRouteRequest(app="team", path="", query={"module": "users", "action": "list"}),
        ActionSeed(module="settings", action="save"),
    )
    assert (result.module, result.action) == ("settings", "save")


def test_route_module_without_action_keeps_query_action():
    result = resolver.resolve(
        BackendRouteRequest(app="team", path="", query={"action": "list"}),
        ModuleSeed(module="users"),
    )
    assert result.kind == "action"
    assert result.module == "users"
    assert result.action == "list"
```

Also cover plugin precedence and invalid identifier -> typed 400 error.

- [ ] **Step 2: Implement normalizer**

Read query values only through typed request data. Apply backend defaults first, then seed override, then the special legacy rule: if route seed specifies module but no action, preserve query action. Construct final union variant exactly once.

Run tests; expected PASS.

---

### Task 6: Implement explicit dispatch registry and Webasyst 4.2.0 resolution order

**Files:**
- Create: `src/gomazon_webasyst/application/ports/dispatch_registry.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/dispatch/__init__.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/dispatch/errors.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/dispatch/keys.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/dispatch/registry.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/dispatch/resolver.py`
- Test: `tests/unit/test_dispatch_registry.py`
- Test: `tests/unit/test_dispatch_resolver.py`

**Interfaces:**
- Registry stores opaque handler IDs/objects keyed by typed app/plugin + module/action semantics.
- `DispatchResolver.resolve(request: DispatchRequest, try_default: bool = False) -> DispatchTarget`.
- Produces `DispatchTargetNotFound` and `PluginUnavailable`.

- [ ] **Step 1: Define application-owned registry Protocol**

Use methods such as:

```python
class DispatchRegistry(Protocol):
    def has_controller(self, key: ControllerKey) -> bool: ...
    def has_action(self, key: ActionKey) -> bool: ...
    def has_actions(self, key: ActionsKey) -> bool: ...
    def handler_id_for_controller(self, key: ControllerKey) -> str: ...
    ...
```

Keep key data classes/models free of FastAPI and PHP class-name assumptions.

- [ ] **Step 2: Write resolver order tests**

For explicit action `post/show`, register all three candidates and prove controller wins. Remove controller and prove single action wins. Remove single action and prove multi-actions wins with `action_method == "show"`. With no explicit handler and `try_default=True`, prove resolver retries the same namespace/module as `DefaultDispatch`. With nothing registered, prove 404 typed error.

- [ ] **Step 3: Implement in-memory registry and resolver**

No dynamic import/class-name generation. Registry is explicit and injectable. Plugin enablement is represented by registry/plugin availability rather than filesystem checks in the core resolver.

Run dispatch tests; expected PASS.

---

### Task 7: Add per-app dispatch strategy override seam

**Files:**
- Create: `src/gomazon_webasyst/compatibility/webasyst/dispatch/strategies.py`
- Test: `tests/unit/test_dispatch_strategies.py`

**Interfaces:**
- `DispatchStrategy` Protocol: `resolve(request: DispatchRequest, try_default: bool = False) -> DispatchTarget`.
- `DispatchStrategyRegistry` returns app-specific strategy or default strategy.

- [ ] **Step 1: Write tests**

Prove app `blog` can use a custom strategy while `site` uses the standard resolver. Prove plugin namespace still selects strategy by owning app ID.

- [ ] **Step 2: Implement registry**

Constructor receives default strategy; `register(app: str, strategy: DispatchStrategy)` installs override. `for_request(request)` extracts owning app from typed namespace and returns exact strategy.

Run tests; expected PASS.

---

### Task 8: Add presentation-only ASGI adapter without mounting catch-all in production main yet

**Files:**
- Create: `src/gomazon_webasyst/presentation/http/legacy_dispatch.py`
- Test: `tests/integration/test_legacy_dispatch_http.py`
- Modify: `AGENTS.md` only if implementation exposes a new architectural decision beyond ADR-014..016.

**Interfaces:**
- `create_legacy_compatibility_router(service: LegacyCompatibilityService) -> APIRouter` or equivalent factory.
- Router converts Starlette request data into `FrontendRouteRequest`/`BackendRouteRequest`, calls compatibility service, and translates typed redirect/errors/dispatch result.
- It is deliberately not mounted as a global catch-all in `main.py` during this slice.

- [ ] **Step 1: Write ASGI tests**

Instantiate a dedicated `FastAPI()` test app with the compatibility router and static in-memory route tables/registry. Cover:

- frontend redirect -> 301/302 response;
- frontend route -> resolved handler response;
- backend query normalization -> correct handler;
- invalid dispatch parameter -> 400;
- route/target not found -> 404;
- existing native contact API remains untouched because production `main.py` has no legacy catch-all yet.

- [ ] **Step 2: Implement thin adapter/service composition**

Transport layer may inspect `Request`, headers, host, path, and query. It must immediately construct typed contracts and hand off to compatibility core. No route-array parsing or handler-order logic belongs in presentation code.

- [ ] **Step 3: Run full suite**

```bash
python -m pytest -v
```

Expected: all existing contact foundation tests plus new routing/dispatch tests PASS.

- [ ] **Step 4: Verify architecture boundaries**

```bash
python -m pytest tests/architecture/test_dependency_boundaries.py -v
python -m compileall -q src
```

Expected: PASS / exit 0.

- [ ] **Step 5: Commit final slice**

Commit only after full verification, then let GitHub Actions execute the same full suite on Python 3.12 before integration into `main`.
