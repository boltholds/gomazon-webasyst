# Application Runtime, Events & Plugins — Design Specification

Status: accepted baseline
Date: 2026-09-19
Repository: `boltholds/gomazon-webasyst`
Authoritative legacy release: Webasyst Framework 4.2.0
Release commit: `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`

## 1. Goal

Add the first explicit Python application runtime layer above `InstalledApplicationCatalog`.

The slice connects four concepts that must remain distinct:

1. **installed application/plugin discovery** — what exists and is enabled in the legacy installation;
2. **Python runtime modules** — what has actually been migrated to executable Python;
3. **runtime registries** — API methods, dispatch handlers and event handlers that can execute;
4. **event dispatch** — Webasyst-compatible event subscription/matching/result behavior without dynamic PHP class loading.

The slice is the bridge from framework foundation work to vertical migration of real Webasyst applications.

It MUST NOT recreate `waSystem`, `waEvent`, or `waPlugin` as global service locators/runtime objects.

## 2. Current Python seams

The rewrite already has:

- canonical `InstalledApplicationCatalog`;
- explicit `ApiMethodRegistry`;
- explicit `DispatchRegistry`;
- typed API Execution;
- typed routing/dispatch compatibility;
- composition root;
- safe declarative PHP config parser;
- exact Webasyst 4.2.0 application discovery characterization.

What is missing:

- installed plugin discovery;
- plugin identity/metadata contracts;
- explicit Python application/plugin runtime modules;
- event handler definitions/registry;
- event dispatch ordering/result semantics;
- a linker that validates runtime modules against installed apps/plugins and populates existing registries;
- a single composition point for migrated app capabilities.

Currently an app may be installed but there is no canonical declaration saying which Python API methods, dispatch handlers, events or plugin implementations belong to it.

## 3. Legacy 4.2.0 event/plugin characterization

### 3.1 Event invocation identity

`waSystem::event()` creates a `waEvent` from:

- event application id;
- event name;
- params;
- optional `array_keys`.

An event is therefore identified by two open values:

```text
(event_app_id, event_name)
```

The event application is the application that owns/emits the event, not necessarily the application implementing a handler.

### 3.2 Handler sources

`waEvent::setHandlers()` collects handlers from:

1. every installed application returned by `getApps(true)`;
2. files under `lib/handlers/*.handler.php`;
3. optional `lib/handlers/wildcard.php`;
4. enabled plugin manifests and their `handlers` declarations.

Python MUST NOT reproduce PHP file/class execution.

Legacy sources are characterization inputs only. Executable Python handlers require explicit runtime registration.

### 3.3 Application handler filename convention

For:

```text
wa-apps/<handler-app>/lib/handlers/<event-app>.<event-name>.handler.php
```

the legacy event system derives:

- event source app from the filename prefix;
- event name from the remainder;
- handler app from the directory owner;
- default handler method `execute`;
- a PHP class name derived from app/event naming.

The Python rewrite preserves the subscription semantics but replaces class-name derivation with explicit `EventHandlerDefinition` registration.

### 3.4 Wildcard application declarations

`wildcard.php` may declare:

- `event`;
- `event_app_id`;
- handler `app_id`;
- `class`;
- `method`;
- optional file.

Python preserves explicit source-app/pattern/owner semantics, not PHP file/class fields.

### 3.5 Plugin enablement and manifests

Enabled plugins are selected from:

```text
wa-config/apps/<app_id>/plugins.php
```

For each truthy plugin entry, Webasyst reads:

```text
wa-apps/<app_id>/plugins/<plugin_id>/lib/config/plugin.php
```

A missing plugin config is skipped.

Plugin metadata includes fields such as:

- `name`;
- `description`;
- `img`;
- `version`;
- `vendor`;
- `rights`;
- `frontend`;
- `cron`;
- `handlers`;
- app-specific settings flags.

### 3.6 Implicit plugin handlers

Legacy normalization adds handlers when capability flags are enabled:

- `rights=true` -> `rights.config -> rightsConfig`;
- `frontend=true` -> `routing -> routing`;
- event discovery also recognizes `cron=true` -> `cron -> cron`.

These are compatibility normalization rules.

### 3.7 Plugin wildcard handlers

Plugin manifest `handlers['*']` may contain structured registrations overriding:

- `event_app_id`;
- event pattern;
- class;
- method.

Webasyst 4.2.0 bundled source contains real examples such as the Site `rublesign` plugin subscribing to events emitted by `webasyst`, `shop`, and `site`.

### 3.8 Match ordering

For an emitted event `(event_app_id, name)`, legacy `waEvent::run()` concatenates handler buckets in this order:

1. exact source app + exact event name;
2. exact source app + wildcard/masked event bucket;
3. wildcard source app + exact event name;
4. wildcard source app + wildcard/masked event bucket.

Registration order inside each bucket is preserved.

The Python event registry/dispatcher MUST preserve this observable ordering.

### 3.9 Pattern behavior

Legacy handler event strings support:

- exact event names;
- suffix mask `prefix.*`;
- raw PCRE when the declaration begins with `/` or `~`.

The first Python event core implements exact and prefix-mask patterns as native typed variants.

Raw PCRE compatibility is isolated behind a compatibility matcher port. It MUST NOT become an arbitrary regex string interpreted directly inside application code.

If 4.2.0 bundled characterization finds no runtime-critical raw PCRE subscriptions, PCRE execution may remain deferred while unsupported declarations are explicit diagnostics rather than silently broadened matches.

### 3.10 Result ownership and first-result semantics

Application handlers:

- results are keyed by handler application id;
- after one non-null result exists for that app, later handlers for the same app do not contribute another result;
- a null result does not block later handlers for that app.

Plugin handlers:

- result identity is plugin-scoped;
- when the emitting app equals plugin app, legacy key is based on plugin id;
- otherwise it includes app id + plugin id;
- legacy response adds `-plugin`;
- only the first non-null result per plugin result identity is retained.

The Python core models this with an explicit `EventResultOwner` rather than string-key tricks.

### 3.11 Handler failures

Legacy application/plugin handler exceptions are logged and event dispatch continues.

Expected handler failure therefore MUST NOT abort unrelated handlers by default.

Python event execution records typed failure diagnostics while compatibility result projection omits failed handlers, matching legacy result behavior.

Unexpected process-level cancellation/system exceptions are not swallowed.

### 3.12 Active-app/plugin global state

Legacy temporarily mutates global active application/plugin state for locale/service lookup.

Python MUST NOT reproduce this global mutable context.

Handlers receive an explicit immutable `EventHandlerContext`.

### 3.13 System before/after event hooks

Legacy `SystemConfig::eventHook` and `eventHookAfter` may override the complete event result.

They are not implemented as hidden globals.

The event architecture reserves explicit ordered interceptor ports for a later compatibility slice.

## 4. Core architectural distinction

Three independent truths exist:

```text
InstalledApplicationCatalog
  = what the legacy installation says exists

InstalledPluginCatalog
  = which legacy plugins are enabled and what their manifests declare

ApplicationRuntimeModuleRegistry
  = which apps/plugins have executable Python implementations
```

An installed app/plugin is not automatically executable in Python.

A Python runtime module for an app/plugin that is not installed/enabled is invalid composition.

This distinction prevents accidental execution of legacy PHP code and allows gradual migration.

## 5. Plugin domain

### 5.1 PluginId VO

Create immutable open VO:

```python
@dataclass(slots=True, frozen=True)
class PluginId:
    value: str
```

The value is validated at the legacy filesystem boundary before path construction.

### 5.2 PluginKey VO

Correlated identity:

```python
@dataclass(slots=True, frozen=True)
class PluginKey:
    app_id: AppId
    plugin_id: PluginId
```

No separate primitive `app_id`/`plugin_id` pairs across plugin ports.

### 5.3 InstalledPlugin Entity

```python
@dataclass(slots=True, frozen=True)
class InstalledPlugin:
    key: PluginKey
    display_name: PluginDisplayName
    version: PluginVersion
    vendor: PluginVendor
    image: PluginImageState
    capabilities: PluginCapabilities
    handler_declarations: PluginHandlerDeclarations
```

This Entity describes normalized legacy installation metadata only.

It contains no executable Python callable or dynamically derived PHP class.

### 5.4 InstalledPluginCatalog port

```python
class InstalledPluginCatalog(Protocol):
    async def resolve(self, key: PluginKey) -> InstalledPluginResolution: ...
    async def for_application(self, app_id: AppId) -> InstalledPluginSnapshot: ...
```

Misses are explicit variants.

Snapshot order follows `plugins.php` order.

## 6. Plugin filesystem discovery

Extend the existing safe declarative PHP parser.

Production discovery:

1. receives canonical installed application snapshot;
2. for each ordinary installed app, reads `wa-config/apps/<app>/plugins.php`;
3. missing plugins file -> empty plugin snapshot for that app;
4. false/falsy entry -> disabled;
5. truthy entry + missing plugin manifest -> skipped, matching legacy behavior;
6. parses plugin manifest declaratively;
7. normalizes metadata and handler declarations;
8. never imports/executes plugin PHP.

The first slice keeps locale translation, plugin update scripts, install hooks, settings UI and file upload settings outside plugin discovery.

## 7. Runtime module model

### 7.1 ApplicationRuntimeModule Entity

An explicit Python module declaration:

```python
@dataclass(slots=True, frozen=True)
class ApplicationRuntimeModule:
    app_id: AppId
    dispatch_handlers: tuple[DispatchRuntimeDefinition, ...]
    api_methods: tuple[ApiMethodDefinition, ...]
    event_handlers: tuple[EventHandlerDefinition, ...]
    plugins: tuple[PluginRuntimeModule, ...]
```

This is not discovered from request strings or PHP filenames.

A migrated application package exports one explicit runtime module from Python composition code.

### 7.2 PluginRuntimeModule Entity

```python
@dataclass(slots=True, frozen=True)
class PluginRuntimeModule:
    key: PluginKey
    dispatch_handlers: tuple[DispatchRuntimeDefinition, ...]
    api_methods: tuple[ApiMethodDefinition, ...]
    event_handlers: tuple[EventHandlerDefinition, ...]
```

Plugin runtime modules are executable Python contributions.

They are validated against `InstalledPluginCatalog` before linking.

### 7.3 No universal runtime object

Runtime modules are immutable declarations.

They do not expose arbitrary service lookup, repositories, request state, settings maps, or global current app/plugin.

Dependencies required by actual handlers are injected when the module is constructed.

## 8. Dispatch runtime definitions

Existing `DispatchRegistry` lookup contract is retained.

Add typed registration definitions instead of making runtime linker know internal registry dictionaries.

Conceptual variants:

- `ControllerDispatchDefinition`;
- `ActionDispatchDefinition`;
- `MultiActionDispatchDefinition`;
- `PluginAvailabilityDefinition`.

Either extend `DispatchRegistry` with typed registration operations or introduce a separate application-owned `DispatchRegistrationSink`.

Lookup and registration responsibilities SHOULD remain separable so request-time consumers do not need mutation APIs.

## 9. API runtime integration

Existing `ApiMethodDefinition` and `ApiMethodRegistry` are reused unchanged.

Runtime linker validates all API method targets before mutating the registry.

An installed app still returns `invalid_method` when no Python method is registered.

No legacy class-name discovery is restored.

## 10. Event domain

### 10.1 Event identity VOs

Open immutable values:

- `EventName`;
- `EventHandlerId`.

Correlated key:

```python
@dataclass(slots=True, frozen=True)
class EventKey:
    app_id: AppId
    name: EventName
```

### 10.2 Event source selector

Explicit variants:

- `ExactEventSource(app_id)`;
- `AnyEventSource`.

No magic `"*"` in application contracts.

### 10.3 Event name pattern

Explicit variants:

- `ExactEventPattern(name)`;
- `PrefixEventPattern(prefix)`;
- compatibility-only `LegacyRegexEventPattern(expression)`.

Pattern matching is owned by an injected Service.

### 10.4 Event owner

Explicit variants:

- `ApplicationEventOwner(app_id)`;
- `PluginEventOwner(plugin_key)`.

This owner controls first-result semantics and compatibility result keys.

### 10.5 Event handler protocol

```python
class EventHandler(Protocol):
    async def handle(
        self,
        context: EventHandlerContext,
        payload: EventPayload,
    ) -> EventHandlerOutcome: ...
```

Internal handlers receive typed payload objects.

Legacy compatibility events may use a bounded `LegacyEventPayload` wrapper over JSON-compatible values until a specific event is migrated to its own typed contract.

Do not use `dict | None` as a generic result.

### 10.6 Handler outcome

Variants:

- `EventHandlerNoResult`;
- `EventHandlerReturned(value)`.

Handler exceptions are captured by dispatcher into diagnostics, not encoded as normal return variants produced by handlers.

### 10.7 EventHandlerDefinition Entity

Contains:

- stable `EventHandlerId`;
- owner;
- source selector;
- event pattern;
- executable handler.

Registration order is explicit and stable.

## 11. Event registry

Application-owned port:

```python
class EventHandlerRegistry(Protocol):
    def register(
        self,
        definition: EventHandlerDefinition,
    ) -> EventHandlerRegistrationResult: ...

    def matching(
        self,
        key: EventKey,
    ) -> EventHandlerMatchSet: ...
```

Duplicate handler id is rejected.

Matching produces definitions already ordered by legacy bucket precedence + registration order.

The dispatcher does not rescan filesystem or manifests.

## 12. Event dispatch Composite

`EventDispatcher` sequence:

1. resolve ordered matching handlers;
2. execute in order;
3. maintain result-owner set;
4. if owner already produced a non-null result, skip later handlers for that owner;
5. `NoResult` leaves owner eligible;
6. successful `Returned` stores one result;
7. handler exception records diagnostic and continues;
8. produce `EventDispatchReport`.

Report contains:

- ordered successful results;
- ordered failure diagnostics;
- optional timing/observability data through a separate observer port.

Compatibility projection converts successful results to legacy keyed mapping.

## 13. Legacy result projection

Create Webasyst compatibility Service that maps explicit owner identities to 4.2.0 keys.

Application owner:

```text
<app_id>
```

Plugin owner when event source app equals plugin app:

```text
<plugin_id>-plugin
```

Cross-app plugin owner:

```text
<app_id>_<plugin_id>-plugin
```

`array_keys` padding remains compatibility projection behavior, not event core behavior.

## 14. Runtime linker

Create one startup Composite: `ApplicationRuntimeLinker`.

Inputs:

- `InstalledApplicationCatalog`;
- `InstalledPluginCatalog`;
- runtime modules;
- dispatch registration sink/builder;
- `ApiMethodRegistry`;
- `EventHandlerRegistry`.

Algorithm:

### Phase 1 — validate all declarations

For every application runtime module:

- app must be installed;
- duplicate app runtime module rejected;
- every API method target must belong to that app;
- every dispatch/event application owner must be structurally valid.

For every plugin runtime module:

- parent app must be installed;
- plugin must be enabled/discovered;
- duplicate plugin runtime module rejected;
- plugin contributions must use its `PluginKey`.

Validate duplicate API/dispatch/event targets before mutating any live registry.

### Phase 2 — link

Only after full validation:

- register dispatch definitions;
- register API methods;
- register event handlers;
- mark executable plugins available to dispatch where declared.

The first implementation is startup-only and immutable after composition.

No runtime hot loading/unloading in this slice.

## 15. Runtime registry/catalog

Composition may expose a read-only `LinkedApplicationRuntimeCatalog` for diagnostics:

- installed but not migrated;
- migrated and linked;
- installed plugin but no Python runtime;
- linked plugin.

This is diagnostic state, not service lookup.

It MUST NOT return arbitrary handler/service instances.

## 16. Composition

Target flow:

```text
webasyst filesystem
      |
      +--> InstalledApplicationCatalog
      |
      +--> InstalledPluginCatalog
                     |
Python runtime modules
      |              |
      +-------+------+
              |
              v
    ApplicationRuntimeLinker
       /       |       \
      v        v        v
 Dispatch   API methods  Events
 Registry   Registry     Registry
```

All request-time execution uses already-linked registries.

No request-time filesystem discovery.

## 17. Relationship to legacy app manifests

`InstalledApplication.capabilities` such as `frontend`, `plugins`, `rights` describe legacy metadata.

They do not automatically create Python runtime contributions.

Example:

```text
frontend=true
```

means the legacy app advertises frontend capability.

It does NOT mean a Python frontend handler exists.

Executable capability is represented only by a linked runtime module.

## 18. Relationship to plugin manifests

Plugin manifest `handlers` are normalized into declarative `PluginHandlerDeclaration` values for compatibility inventory and migration tooling.

They are NOT executable.

A migration tool/report can compare:

```text
legacy declared handler
vs
Python registered EventHandlerDefinition
```

This creates a measurable migration checklist per plugin.

## 19. Security boundaries

Required:

1. no PHP execution;
2. no class/module import from legacy strings;
3. no request string controls import/module path;
4. plugin/app ids pass safe path policy;
5. runtime modules are imported only by explicit Python composition code;
6. event raw-regex compatibility is isolated and bounded;
7. handler exceptions do not expose traceback through compatibility result;
8. runtime linker fails fast on duplicate/foreign registrations;
9. installed-but-unmigrated plugins cannot become dispatch-available accidentally.

## 20. First-slice non-goals

Not included yet:

- plugin install/update/uninstall lifecycle;
- executing legacy PHP plugin code;
- plugin settings UI;
- plugin file upload settings;
- plugin database update scripts;
- plugin templates/assets rendering;
- live plugin enable/disable reload;
- event cache files;
- SystemConfig `eventHook/eventHookAfter`;
- full PCRE parity unless characterization proves necessary;
- cron scheduler execution;
- CLI command execution;
- widget runtime;
- theme runtime;
- automatic route loading from legacy PHP routing files;
- arbitrary runtime package discovery through import scanning.

## 21. TDD characterization

Pin exact 4.2.0 behavior for:

- `waEvent::run` bucket ordering;
- application handler filename parsing;
- wildcard.php declarations;
- plugin `handlers` simple form;
- plugin wildcard form;
- `rights`, `frontend`, `cron` implicit handlers;
- plugin enable/disable/missing-manifest behavior;
- app/plugin first-result semantics;
- exception continuation;
- compatibility result keys;
- `array_keys` result padding;
- any raw PCRE uses in bundled 4.2.0.

## 22. Architecture tests

Enforce:

- event/application runtime application packages import no FastAPI/Starlette/SQLAlchemy;
- no dynamic import primitives in runtime linker/discovery;
- no PHP execution;
- installed catalogs contain metadata, not callables;
- runtime modules contain Python execution definitions, not filesystem paths;
- request-time code cannot mutate startup runtime registries;
- API/dispatch/event registries remain distinct types;
- runtime linker is the only production path that links application modules into registries.

## 23. Acceptance criteria

Complete when:

- enabled plugins can be discovered safely from a 4.2.0 filesystem tree;
- installed plugin metadata/handler declarations are typed;
- application/plugin Python runtime modules are explicit;
- one startup linker validates installation before registration;
- existing API method registry is populated through runtime modules;
- existing dispatch registry is populated through runtime modules;
- event handler registry + dispatcher preserve characterized ordering and first-result behavior;
- plugin/app handler exceptions continue dispatch with diagnostics;
- installed but unmigrated plugin remains non-executable;
- no dynamic PHP/Python class discovery is introduced;
- cross-runtime integration proves one application can expose API + dispatch + event handler through one explicit runtime module;
- full CI is green.

## 24. Follow-on

After this layer is merged, migrate the first real application vertical slice.

Recommended proof:

- one bundled application module;
- one real API method or backend/frontend action;
- one event emitted/handled;
- optionally one bundled plugin handler;
- real legacy DB rows;
- compatibility response.

That becomes the template for systematic bundled-app migration.
