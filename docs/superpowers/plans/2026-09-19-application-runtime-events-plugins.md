# Application Runtime, Events & Plugins Implementation Plan

> **For agentic workers:** execute task-by-task with TDD. Steps use checkbox (`- [x]`) tracking.

**Goal:** Add explicit Python application/plugin runtime modules, safe installed-plugin discovery, a deterministic Webasyst-compatible event registry/dispatcher, and one startup linker that populates existing API/dispatch registries plus the new event registry.

**Spec:** `docs/superpowers/specs/2026-09-19-application-runtime-events-plugins-design.md`

**Authoritative legacy source:** Webasyst Framework 4.2.0 release commit `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`.

## Global constraints

- Do not execute PHP.
- Do not derive Python imports/classes from app/plugin/request strings.
- Installed metadata and executable Python runtime remain separate.
- Expected negative states are explicit typed variants, never `None`/False/empty sentinels.
- Runtime registries are startup-built and request-time read-only.
- API, dispatch and event registries remain distinct.
- Runtime linker validates the complete graph before mutating live registries.
- Event application/domain code imports no FastAPI/Starlette/SQLAlchemy/compatibility modules.
- Plugin/app filesystem paths remain compatibility/infrastructure-private.
- Exact Webasyst event bucket ordering and first-result semantics are compatibility requirements.
- Handler exceptions do not abort unrelated handlers by default.
- Raw PCRE is never interpreted directly by application code.
- Plugin lifecycle/update/settings/templates/assets/widgets/cron execution/CLI/live reload remain out of scope.

---

### Task 0: Characterize Webasyst 4.2.0 event and plugin behavior

**Files:**
- Create: `docs/superpowers/specs/2026-09-19-application-runtime-events-plugins-characterization.md`
- Create: `tests/fixtures/webasyst_4_2/runtime_events_plugins/`
- Create: `tests/compatibility/test_runtime_events_plugins_characterization.py`

**Source cases to pin:**
- `waEvent::run()` handler bucket ordering;
- `lib/handlers/<source>.<event>.handler.php` parsing;
- application `wildcard.php`;
- `wa-config/apps/<app>/plugins.php` truthy/falsy enablement;
- missing plugin config skip;
- simple plugin `handlers`;
- wildcard plugin handlers with cross-app `event_app_id`;
- implicit `rights.config`, `routing`, `cron`;
- first non-null result per application;
- first non-null result per plugin;
- cross-app plugin result key;
- exception continuation;
- `array_keys` padding;
- raw PCRE usage survey in bundled 4.2.0.

- [x] Extract source-reduced fixtures from exact 4.2.0 release commit.
- [x] Record a source-location/behavior/implementation-consequence table.
- [x] Explicitly record whether bundled 4.2.0 uses raw PCRE event patterns.
- [x] Add fixture provenance tests pinned to the release SHA.
- [x] Reconcile any finding that contradicts the design before implementation.
- [x] Commit: `test: characterize legacy events and plugins`.

---

### Task 1: Plugin identity and InstalledPlugin domain

**Files:**
- Create: `src/gomazon_webasyst/application/plugins/__init__.py`
- Create: `src/gomazon_webasyst/application/plugins/entities/installed_plugin.py`
- Create: `src/gomazon_webasyst/application/plugins/vo/identity.py`
- Create: `src/gomazon_webasyst/application/plugins/vo/metadata.py`
- Create: `src/gomazon_webasyst/application/plugins/vo/capabilities.py`
- Create: `src/gomazon_webasyst/application/plugins/vo/handlers.py`
- Create: `src/gomazon_webasyst/application/ports/installed_plugin_catalog.py`
- Create: `tests/unit/test_installed_plugin_types.py`
- Create: `tests/architecture/test_plugin_domain_boundaries.py`

**Types:**
- `PluginId`;
- `PluginKey(AppId, PluginId)`;
- `PluginDisplayName`;
- `PluginVendor`;
- `PluginVersion`;
- explicit image state;
- `PluginCapabilityName`;
- normalized declarative handler declarations;
- `InstalledPlugin` Entity;
- resolved/missing/snapshot catalog contracts.

- [x] Write RED tests for immutable identity and validation.
- [x] Pin no-null image state and empty immutable collections.
- [x] Pin `PluginKey` as the only cross-port plugin identity.
- [x] Add architecture guard against transport/ORM/filesystem imports.
- [x] Implement minimal Entity/VO/catalog contracts.
- [x] Run GREEN.
- [x] Commit: `feat: add installed plugin contracts`.

---

### Task 2: Safe installed-plugin discovery

**Files:**
- Create: `src/gomazon_webasyst/compatibility/webasyst/plugins/__init__.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/plugins/paths.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/plugins/normalizer.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/plugins/raw_config.py`
- Create: `src/gomazon_webasyst/infrastructure/plugins/__init__.py`
- Create: `src/gomazon_webasyst/infrastructure/plugins/in_memory_catalog.py`
- Create: `src/gomazon_webasyst/infrastructure/plugins/filesystem_catalog.py`
- Create: `tests/unit/test_plugin_config_normalizer.py`
- Create: `tests/unit/test_plugin_paths.py`
- Create: `tests/integration/test_installed_plugin_filesystem.py`

**Discovery:**
- consumes installed application snapshot;
- reads `wa-config/apps/<app>/plugins.php`;
- parses via existing restricted PHP parser;
- resolves `wa-apps/<app>/plugins/<plugin>/lib/config/plugin.php`;
- normalizes metadata/handlers only;
- performs no code import/execution.

- [x] RED: enabled/falsy/missing plugins.
- [x] RED: plugin-id path traversal and symlink escape.
- [x] RED: simple/wildcard handler declarations.
- [x] RED: implicit rights/frontend/cron declarations.
- [x] Implement pure normalizer.
- [x] Implement immutable startup filesystem catalog.
- [x] Run GREEN + characterization tests.
- [x] Commit: `feat: discover installed webasyst plugins`.

---

### Task 3: Event identity, patterns and handler contracts

**Files:**
- Create: `src/gomazon_webasyst/application/events/__init__.py`
- Create: `src/gomazon_webasyst/application/events/entities/handler_definition.py`
- Create: `src/gomazon_webasyst/application/events/vo/identity.py`
- Create: `src/gomazon_webasyst/application/events/vo/patterns.py`
- Create: `src/gomazon_webasyst/application/events/vo/owners.py`
- Create: `src/gomazon_webasyst/application/events/vo/payload.py`
- Create: `src/gomazon_webasyst/application/events/services/pattern_matcher.py`
- Create: `src/gomazon_webasyst/application/ports/event_handlers.py`
- Create: `tests/unit/test_event_types.py`
- Create: `tests/architecture/test_event_domain_boundaries.py`

**Core types:**
- `EventName`;
- `EventKey`;
- `EventHandlerId`;
- `ExactEventSource | AnyEventSource`;
- `ExactEventPattern | PrefixEventPattern | LegacyRegexEventPattern`;
- `ApplicationEventOwner | PluginEventOwner`;
- `EventHandlerNoResult | EventHandlerReturned`;
- `EventHandlerDefinition`;
- `EventHandler` Protocol.

- [x] RED: equality/hash/frozen validation.
- [x] RED: no magic `"*"` state in application contracts.
- [x] RED: exact/prefix matching.
- [x] RED: raw regex delegates to compatibility matcher port.
- [x] Implement minimal types/services.
- [x] Run GREEN.
- [x] Commit: `feat: add event handler contracts`.

---

### Task 4: EventHandlerRegistry with legacy bucket ordering

**Files:**
- Create: `src/gomazon_webasyst/infrastructure/events/__init__.py`
- Create: `src/gomazon_webasyst/infrastructure/events/registry.py`
- Create: `tests/unit/test_event_handler_registry.py`

**Ordering:**
1. exact source/exact event;
2. exact source/pattern bucket;
3. any source/exact event;
4. any source/pattern bucket.

Registration order remains stable within bucket.

- [x] RED: exact-only resolution.
- [x] RED: full four-bucket order.
- [x] RED: duplicate handler id rejected.
- [x] RED: multiple matching prefix patterns preserve registration order.
- [x] Implement in-memory immutable/read-mostly registry.
- [x] Run GREEN.
- [x] Commit: `feat: add event handler registry`.

---

### Task 5: EventDispatcher and first-result semantics

**Files:**
- Create: `src/gomazon_webasyst/application/events/composites/dispatcher.py`
- Create: `src/gomazon_webasyst/application/events/composites/contracts.py`
- Create: `tests/unit/test_event_dispatcher.py`

**Behavior:**
- invoke ordered matches;
- no-result allows later same-owner handlers;
- first returned value closes that owner;
- later handlers for closed owner are skipped;
- different owners continue;
- handler exception -> diagnostic + continue;
- cancellation/system exceptions propagate;
- report keeps ordered results + failures.

- [x] RED: application owner first-result.
- [x] RED: plugin owner first-result.
- [x] RED: no-result fallthrough.
- [x] RED: exception continuation.
- [x] RED: deterministic mixed-owner ordering.
- [x] Implement dispatcher.
- [x] Run GREEN.
- [x] Commit: `feat: dispatch registered application events`.

---

### Task 6: Webasyst event compatibility projection

**Files:**
- Create: `src/gomazon_webasyst/compatibility/webasyst/events/__init__.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/events/result_projection.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/events/pattern_matcher.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/events/payload.py`
- Create: `tests/unit/test_legacy_event_result_projection.py`
- Create: `tests/unit/test_legacy_event_pattern_matcher.py`

**Projection keys:**
- app owner -> `app_id`;
- same-app plugin -> `plugin_id-plugin`;
- cross-app plugin -> `app_id_plugin_id-plugin`.

`array_keys` padding belongs here.

- [x] RED: all result key variants.
- [x] RED: `array_keys` scalar/list padding behavior from characterization.
- [x] Implement exact/prefix compatibility mapping.
- [x] Implement only characterized bounded regex support; explicit unsupported result otherwise.
- [x] Run GREEN.
- [x] Commit: `feat: project legacy event results`.

---

### Task 7: Runtime module entities

**Files:**
- Create: `src/gomazon_webasyst/application/runtime/__init__.py`
- Create: `src/gomazon_webasyst/application/runtime/entities/application_module.py`
- Create: `src/gomazon_webasyst/application/runtime/entities/plugin_module.py`
- Create: `src/gomazon_webasyst/application/runtime/vo/dispatch.py`
- Create: `tests/unit/test_application_runtime_modules.py`
- Create: `tests/architecture/test_application_runtime_boundaries.py`

**Entities:**
- `ApplicationRuntimeModule`;
- `PluginRuntimeModule`;
- typed dispatch registration variants.

They aggregate already-constructed executable definitions; they do not discover/import them.

- [x] RED: immutable module identity.
- [x] RED: plugin contribution owner matches `PluginKey`.
- [x] RED: API targets must be structurally app-owned.
- [x] Add dependency guard.
- [x] Implement minimal module model.
- [x] Run GREEN.
- [x] Commit: `feat: add application runtime module declarations`.

---

### Task 8: Dispatch registration sink/builder

**Files:**
- Create: `src/gomazon_webasyst/application/ports/dispatch_registration.py`
- Modify: `src/gomazon_webasyst/compatibility/webasyst/dispatch/registry.py`
- Create: `tests/unit/test_dispatch_registration.py`

**Goal:** separate request-time lookup from startup mutation.

- [x] RED: typed controller/action/multi-action/plugin registration.
- [x] RED: duplicate target registration rejected rather than overwritten.
- [x] Preserve existing `DispatchRegistry` lookup contract.
- [x] Implement registration sink on in-memory registry/builder.
- [x] Run existing routing/dispatch suite.
- [x] Commit: `refactor: add typed dispatch registration`.

---

### Task 9: ApplicationRuntimeLinker full validation then link

**Files:**
- Create: `src/gomazon_webasyst/application/runtime/composites/linker.py`
- Create: `src/gomazon_webasyst/application/runtime/composites/results.py`
- Create: `tests/unit/test_application_runtime_linker.py`

**Validation before mutation:**
- app module app exists;
- duplicate app module rejected;
- plugin runtime plugin exists/enabled;
- duplicate plugin module rejected;
- API targets owned by declared app/plugin parent;
- dispatch definitions structurally owned;
- event owners structurally owned;
- duplicate API/dispatch/event targets detected before apply.

- [x] RED: installed app links.
- [x] RED: uninstalled app rejected.
- [x] RED: disabled/missing plugin rejected.
- [x] RED: duplicate runtime definitions leave all registries unchanged.
- [x] RED: foreign contribution rejected.
- [x] Implement validate-plan-apply composite.
- [x] Run GREEN.
- [x] Commit: `feat: link application runtime modules`.

---

### Task 10: Composition runtime graph

**Files:**
- Create: `src/gomazon_webasyst/composition/application_runtime.py`
- Modify: `src/gomazon_webasyst/composition/container.py`
- Modify: `src/gomazon_webasyst/composition/api_execution.py`
- Wire existing dispatch composition where appropriate.
- Create: `tests/unit/test_application_runtime_composition.py`

**Composition:**
- build InstalledApplicationCatalog;
- build InstalledPluginCatalog;
- construct explicit Python runtime modules;
- construct fresh API/dispatch/event registries;
- link modules;
- inject linked registries into consumers;
- expose read-only event dispatcher/runtime diagnostics.

Initial production runtime module tuple may be empty until first real app slice.

- [x] RED: one catalog/plugin/runtime graph per Container.
- [x] RED: installed-but-no-module stays non-executable.
- [x] RED: explicit test injection avoids real filesystem.
- [x] Implement composition.
- [x] Run full existing foundation suite.
- [x] Commit: `feat: compose application runtime graph`.

---

### Task 11: Cross-runtime proof module

**Files:**
- Create: `tests/integration/test_application_runtime_cross_registry.py`
- Add a test-only Python application runtime module.

**Proof module must declare:**
- one API method;
- one dispatch registration;
- one event handler.

Test:
1. app is installed in a temporary Webasyst root;
2. runtime linker accepts its Python module;
3. API registry resolves method;
4. dispatch registry resolves handler;
5. emitted event invokes event handler;
6. removing runtime module leaves app installed but all three executable capabilities absent.

- [x] Write RED integration proof.
- [x] Implement only minimal missing wiring.
- [x] Run GREEN.
- [x] Commit: `test: verify linked application runtime capabilities`.

---

### Task 12: Installed plugin vs migrated plugin proof

**Files:**
- Create: `tests/integration/test_plugin_runtime_linking.py`

Scenario:
- plugin enabled in `plugins.php`;
- manifest declares event handlers;
- no Python PluginRuntimeModule -> metadata visible, handler not executable;
- add explicit PluginRuntimeModule -> event handler becomes executable;
- disabled plugin -> linker rejects Python plugin runtime.

- [x] Write integration tests.
- [x] Run GREEN.
- [x] Commit: `test: verify plugin runtime requires explicit migration`.

---

### Task 13: Architecture/security guards

**Files:**
- Create: `tests/architecture/test_application_runtime_security.py`
- Extend relevant no-optional/dynamic-loading guards.
- Modify: `AGENTS.md`.

Guards:
- no `eval`/`exec`/`subprocess`/dynamic import in runtime/plugin/event discovery;
- installed metadata entities contain no callable fields;
- runtime module package contains no filesystem parsing;
- request-time presentation code cannot register runtime definitions;
- API/dispatch/event registries are distinct;
- runtime linker is the production link point;
- no `None` result contracts.

- [x] Write guard tests.
- [x] Fix violations.
- [x] Run architecture suite.
- [x] Commit: `test: guard application runtime boundaries`.

---

### Task 14: Full acceptance and completion record

- [x] Run repository compile/static checks.
- [x] Run `python -m pytest -q`.
- [x] Run focused plugin/event/runtime suites.
- [x] Search repository for dynamic PHP/Python runtime loading primitives.
- [x] Verify request-time paths perform no filesystem discovery.
- [x] Verify existing routing/API/OAuth/auth/ACL/application-registry tests remain green.
- [x] Mark all plan checkboxes complete.
- [x] Mark design spec implemented.
- [x] Record exact passing test count in `AGENTS.md`.
- [x] Commit: `docs: record application runtime verification`.

## Verification record

Implementation head before completion-documentation commits: `ea2c1a4d424f50530b5df08b80dcd4c9664871e5`.

GitHub Actions full CI completed successfully on that head:

- source tree compile passed;
- `782 passed, 9 warnings`;
- exact Webasyst 4.2.0 event/plugin characterization tests passed;
- safe installed-plugin discovery tests passed;
- event ordering/first-result/failure-continuation tests passed;
- runtime module/linker atomicity tests passed;
- shared application-runtime composition tests passed;
- cross-registry app runtime proof passed;
- installed-plugin-vs-explicit-Python-runtime proof passed;
- architecture/security guards passed.

The exact source behavior is pinned to Webasyst Framework 4.2.0 release commit `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`.

## Completion definition

Complete only when:

- installed plugin discovery is source-characterized and safe;
- installed plugin metadata is typed and immutable;
- explicit Python application/plugin runtime modules exist;
- API/dispatch/event contributions link through one startup Composite;
- event ordering/first-result/failure continuation match 4.2.0 characterization;
- installed-but-unmigrated plugin is non-executable;
- no dynamic PHP/Python class discovery exists;
- full CI is green.

## Follow-on

Port the first real bundled application vertical slice using this runtime module system.
