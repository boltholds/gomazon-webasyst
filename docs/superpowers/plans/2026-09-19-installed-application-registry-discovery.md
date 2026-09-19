# Installed Application Registry & Legacy Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the independent empty API/OAuth application registries with one canonical, immutable `InstalledApplicationCatalog` discovered from a configured Webasyst 4.2.0 installation, while preserving explicit API method/dispatch registries and all existing authorization order.

**Architecture:** Legacy filesystem/PHP configuration is parsed and normalized only in compatibility/infrastructure. Application code owns immutable InstalledApplication Entity/VOs plus the catalog port. One startup snapshot is constructed in composition and shared by API Execution and an OAuth-specific projection. No arbitrary PHP execution, request-time filesystem lookup, dynamic Python imports, global service locator, or installer hot reload is introduced.

**Tech Stack:** Python 3.12+, frozen/slotted dataclasses, Pydantic v2 only where cross-boundary serialization is required, `pathlib`, a bounded stdlib recursive-descent parser for the supported declarative PHP return-array subset, pytest.

**Spec:** `docs/superpowers/specs/2026-09-19-installed-application-registry-discovery-design.md`

## Global Constraints

- The supplied Webasyst Framework 4.2.0 source is authoritative over current upstream master when behavior differs.
- All new application-registry domain/application types MUST be classifiable as Entity, VO, Service, or Composite.
- `InstalledApplicationCatalog` is the only canonical production source of installed app identity/metadata.
- `ApiMethodRegistry`, `DispatchRegistry`, and OAuth consent projection remain separate concepts and MUST NOT be folded into the installed-app catalog.
- Expected app lookup misses use explicit typed variants; never `None`, `False`, empty-string sentinels, or exceptions.
- Application registry code imports no FastAPI/Starlette, SQLAlchemy, filesystem parser implementation, or Webasyst compatibility module.
- Raw PHP arrays/parser AST/filesystem paths MUST NOT cross into application code.
- Arbitrary PHP MUST NOT be evaluated or executed, directly or through a subprocess.
- Request/app strings MUST NOT become Python module/class import paths.
- Discovery is a one-time immutable startup snapshot per Container in this slice.
- No request-time mtime polling, installer mutation, live reload, plugin/event/cron discovery, route-table discovery, or bundled-app migration is included.
- Config size, parser nesting depth, app-id path safety, and symlink/root escape behavior MUST be bounded/tested.
- API authorization order remains: installed app -> app access -> token scope -> license -> method lookup -> HTTP method validation -> execute.
- OAuth scope ordering and silent drop of missing/unauthorized apps remain unchanged.
- The `webasyst` OAuth settings-header icon special case remains in compatibility projection, not in the canonical entity.
- Existing full CI must stay green after every cutover task.

## Review Focus

These are the highest-risk conditions to pin before the slice is considered complete:

1. API Execution and OAuth must resolve the same `AppId` from the same catalog instance; no independent production app universe may remain.
2. A configured app id must never escape the Webasyst root through `../`, separators, symlinks, alternate path forms, or parser-crafted input.
3. Unsupported/dynamic PHP expressions must fail closed; they must never be executed or silently interpreted as empty config.
4. The `webasyst` framework app must be present according to characterized 4.2.0 behavior and OAuth must select the characterized settings header icon without polluting the canonical catalog with OAuth-only rules.
5. A malformed installation config is a startup/configuration fault, while an ordinary unknown `AppId` requested by API/OAuth is a typed lookup miss. These two states must never collapse into one another.
6. Existing API method registry and dispatch registry behavior must remain independent; discovery of an installed app must not implicitly make an API method executable.
7. Configured-app order must survive discovery/snapshot normalization so downstream consumers can rely on deterministic legacy ordering.

---

### Task 0: Pin Webasyst 4.2.0 application-discovery characterization

**Files:**
- Create: `tests/fixtures/webasyst_4_2/application_registry/apps_enabled_disabled.php`
- Create: `tests/fixtures/webasyst_4_2/application_registry/app_scalar_icon.php`
- Create: `tests/fixtures/webasyst_4_2/application_registry/app_icon_map.php`
- Create: `tests/fixtures/webasyst_4_2/application_registry/app_img_fallback.php`
- Create: `tests/fixtures/webasyst_4_2/application_registry/app_header_items.php`
- Create: `tests/fixtures/webasyst_4_2/application_registry/webasyst_app.php`
- Create: `tests/fixtures/webasyst_4_2/application_registry/unsupported_dynamic.php`
- Create: `tests/compatibility/test_application_registry_source_characterization.py`
- Create: `docs/superpowers/specs/2026-09-19-installed-application-registry-characterization.md`

**Purpose:**
Before production code, copy the smallest source-backed fixture fragments needed from the supplied 4.2.0 archive and record exact outcomes for ambiguous behavior. Do not use current upstream master to decide a 4.2.0 edge case.

**Must characterize:**
- configured enabled and disabled/falsy entries from `wa-config/apps.php`;
- missing `wa-config/apps.php`;
- enabled app whose `lib/config/app.php` is missing;
- `webasyst` inclusion and exact manifest source path;
- whether `build.php` changes metadata required by current consumers;
- scalar `icon`, size-keyed icon map, and `img` fallback behavior;
- nested `header_items`, especially `webasyst.header_items.settings.icon`;
- localization of `name` and whether this first Python slice can intentionally defer locale translation while keeping the raw manifest name;
- 4.2.0 Installer auto-enable behavior, if present;
- malformed/non-array manifest handling.

- [x] **Step 1: Extract exact minimal fixtures from supplied 4.2.0 source**

Keep source comments identifying original legacy file/method where useful. Do not copy unrelated application code.

- [x] **Step 2: Record source observations**

Write `2026-09-19-installed-application-registry-characterization.md` with a table:

`case | 4.2.0 source location | exact observed behavior | implementation consequence`.

Every behavior later asserted by compatibility tests must have a source row.

- [x] **Step 3: Add source-characterization guard**

The first test may validate fixture provenance/shape and deliberately skip parser assertions until Task 2. It should make missing fixtures or undocumented ambiguous behavior fail review rather than silently default.

- [x] **Step 4: Review spec against findings**

If supplied 4.2.0 behavior differs from the accepted spec, update the spec and `AGENTS.md` before implementing. Do not hide the discrepancy inside code.

- [x] **Step 5: Commit**

```bash
git add tests/fixtures/webasyst_4_2/application_registry \
  tests/compatibility/test_application_registry_source_characterization.py \
  docs/superpowers/specs/2026-09-19-installed-application-registry-characterization.md \
  docs/superpowers/specs/2026-09-19-installed-application-registry-discovery-design.md \
  AGENTS.md
git commit -m "test: characterize legacy application discovery"
```


**Task 0 result:** Characterization is pinned to release commit `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`. It confirmed the missing-config exception, forced `webasyst` inclusion, PHP-truthy enablement, WAID Installer auto-enable, silent missing-manifest skip, locale-specific legacy name translation, asset normalization, and build injection. The design was refined so the shared canonical Python catalog is locale-neutral and excludes build/cache metadata; locale projection is explicitly deferred.


---

### Task 1: Canonical InstalledApplication Entity, VOs and catalog port

**Files:**
- Create: `src/gomazon_webasyst/application/application_registry/__init__.py`
- Create: `src/gomazon_webasyst/application/application_registry/entities/__init__.py`
- Create: `src/gomazon_webasyst/application/application_registry/entities/installed_application.py`
- Create: `src/gomazon_webasyst/application/application_registry/vo/__init__.py`
- Create: `src/gomazon_webasyst/application/application_registry/vo/metadata.py`
- Create: `src/gomazon_webasyst/application/application_registry/vo/icons.py`
- Create: `src/gomazon_webasyst/application/application_registry/vo/capabilities.py`
- Create: `src/gomazon_webasyst/application/application_registry/vo/header_items.py`
- Create: `src/gomazon_webasyst/application/ports/installed_application_catalog.py`
- Modify: `src/gomazon_webasyst/contracts/enums.py`
- Create: `tests/unit/test_installed_application_types.py`
- Create: `tests/architecture/test_application_registry_taxonomy.py`
- Modify: `tests/architecture/test_no_optional_result_contracts.py`

**Interfaces:**
- Entity `InstalledApplication(app_id, display_name, icons, vendor, version, capabilities, header_items)`.
- Open immutable VOs:
  - `ApplicationDisplayName`;
  - `ApplicationVendor`;
  - `ApplicationVersion`;
  - `ApplicationIconReference`;
  - `ApplicationHeaderItemId`;
  - `ApplicationCapabilityName`.
- Immutable collection VOs:
  - `ApplicationIcon(size, reference)`;
  - `ApplicationIconSet(items)`;
  - `ApplicationCapabilities(values)`;
  - `ApplicationHeaderItem(item_id, display_name, icons)`;
  - `ApplicationHeaderItems(items)`.
- Closed `EnumStr` lookup discriminator `InstalledApplicationLookupKind.RESOLVED | MISSING`.
- Port:
  - `async resolve(AppId) -> InstalledApplicationResolved | InstalledApplicationMissing`;
  - `async snapshot() -> InstalledApplicationSnapshot`.

**Rules:**
- no nullable metadata bag;
- icon set/header items/capabilities use empty immutable collections when legitimately empty;
- duplicate icon sizes/header item ids are invalid;
- snapshot preserves input order;
- catalog lookup result exposes Entity, not raw metadata primitives.

- [ ] **Step 1: Write failing Entity/VO immutability and validation tests**

Pin:
- stable identity is `AppId`;
- values are hashable/frozen where appropriate;
- empty display name is rejected;
- icon size must be positive;
- duplicate icon size rejected;
- duplicate header item id rejected;
- open capability names are accepted without central enum changes.

- [ ] **Step 2: Write failing catalog contract tests**

Pin explicit resolved/missing variants and ordered immutable snapshot.

- [ ] **Step 3: Write failing taxonomy/dependency guard**

Reject FastAPI, Starlette, SQLAlchemy, pathlib/filesystem adapter imports, and `gomazon_webasyst.compatibility` inside `application/application_registry`.

- [ ] **Step 4: Run RED**

```bash
python -m pytest \
  tests/unit/test_installed_application_types.py \
  tests/architecture/test_application_registry_taxonomy.py \
  tests/architecture/test_no_optional_result_contracts.py -v
```

Expected: FAIL because the canonical application-registry types do not yet exist.

- [ ] **Step 5: Implement minimal Entity/VO/port foundation**

Use frozen/slotted dataclasses for internal domain state. Do not introduce filesystem discovery yet.

- [ ] **Step 6: Run GREEN**

Run Step 4 command.

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/gomazon_webasyst/application/application_registry \
  src/gomazon_webasyst/application/ports/installed_application_catalog.py \
  src/gomazon_webasyst/contracts/enums.py \
  tests/unit/test_installed_application_types.py \
  tests/architecture/test_application_registry_taxonomy.py \
  tests/architecture/test_no_optional_result_contracts.py
git commit -m "feat: add installed application catalog contracts"
```

---

### Task 2: In-memory canonical catalog for tests and explicit composition injection

**Files:**
- Create: `src/gomazon_webasyst/infrastructure/application_registry/__init__.py`
- Create: `src/gomazon_webasyst/infrastructure/application_registry/in_memory_catalog.py`
- Create: `tests/unit/test_installed_application_catalog.py`

**Interfaces:**
- `InMemoryInstalledApplicationCatalog(applications: tuple[InstalledApplication, ...])`.
- Construction rejects duplicate `AppId`.
- `resolve()` and `snapshot()` are async to match the application-owned port.
- Internal lookup may use a dict, but snapshot order is the constructor order.

- [ ] **Step 1: Write failing resolve/snapshot tests**

Pin:
- resolved entity identity;
- explicit missing result;
- deterministic order;
- duplicate app rejection;
- caller mutation cannot change catalog state.

- [ ] **Step 2: Run RED**

```bash
python -m pytest tests/unit/test_installed_application_catalog.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement minimal in-memory catalog**

No Webasyst/path/config logic here.

- [ ] **Step 4: Run GREEN**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/gomazon_webasyst/infrastructure/application_registry \
  tests/unit/test_installed_application_catalog.py
git commit -m "feat: add in-memory installed application catalog"
```

---

### Task 3: Restricted declarative PHP return-array parser

**Files:**
- Create: `src/gomazon_webasyst/compatibility/webasyst/application_registry/__init__.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/application_registry/php_values.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/application_registry/config_parser.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/application_registry/errors.py`
- Create: `tests/unit/test_legacy_php_config_parser.py`
- Extend: `tests/compatibility/test_application_registry_source_characterization.py`

**Parser model:**
Keep parser output compatibility-private and immutable. Prefer an ordered PHP-array representation rather than immediately coercing to a Python dict:

```python
PhpScalar = str | int | float | bool | None

@dataclass(slots=True, frozen=True)
class PhpArrayEntry:
    key: PhpArrayKeyState
    value: PhpValue

@dataclass(slots=True, frozen=True)
class PhpArray:
    entries: tuple[PhpArrayEntry, ...]
```

Use explicit keyed/unkeyed entry state instead of a nullable key field.

**Supported syntax:**
- optional `<?php`;
- comments: `//`, `#`, `/* ... */`;
- one top-level `return <value>;`;
- `array(...)` and `[...]`;
- `=>`;
- single/double-quoted strings for the subset present in characterized fixtures;
- int/float;
- `true`, `false`, `null`;
- nested arrays;
- trailing commas.

**Rejected syntax:**
- variables;
- constants other than supported scalar literals;
- concatenation;
- function calls;
- object/static access;
- includes/requires;
- executable statements;
- interpolated expressions not explicitly supported.

**Limits:**
- maximum file bytes;
- maximum nesting depth;
- maximum token count/array entries.

- [ ] **Step 1: Write parser RED tests for supported syntax**

Use both synthetic tiny inputs and source-backed fixtures from Task 0.

- [ ] **Step 2: Write fail-closed tests**

Pin:
- `return some_function();`;
- `return $config;`;
- concatenation;
- include/require;
- multiple executable statements;
- unterminated strings/comments;
- depth/size limit exhaustion.

All must raise explicit compatibility parser errors, never return an empty array.

- [ ] **Step 3: Add a no-execution architecture/security assertion**

Statically reject use of `eval`, `exec`, `subprocess`, PHP command invocation, `importlib` and dynamic `__import__` in the parser package.

- [ ] **Step 4: Run RED**

```bash
python -m pytest \
  tests/unit/test_legacy_php_config_parser.py \
  tests/compatibility/test_application_registry_source_characterization.py -v
```

Expected: FAIL.

- [ ] **Step 5: Implement bounded tokenizer + recursive-descent parser**

Do not use a general PHP runtime/parser that executes or resolves PHP code.

- [ ] **Step 6: Run GREEN**

Run Step 4 command.

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/gomazon_webasyst/compatibility/webasyst/application_registry \
  tests/unit/test_legacy_php_config_parser.py \
  tests/compatibility/test_application_registry_source_characterization.py
git commit -m "feat: parse declarative webasyst php config safely"
```

---

### Task 4: Legacy app-id/path policy and root containment

**Files:**
- Create: `src/gomazon_webasyst/compatibility/webasyst/application_registry/paths.py`
- Create: `tests/unit/test_application_registry_paths.py`

**Interfaces:**
- A compatibility path service accepts only already-created `AppId` plus configured root and produces internal legacy config paths.
- Ordinary app manifest: `wa-apps/<app>/lib/config/app.php`.
- Framework app manifest: characterized `wa-system/webasyst/lib/config/app.php`.
- No `Path` crosses into application catalog/entity types.

**Security policy:**
Do not globally over-tighten the open `AppId` VO unless required elsewhere. Apply a filesystem-safe legacy app-id policy at this boundary.

Reject ids containing:
- `/` or `\\`;
- `..` path traversal forms;
- NUL/control characters;
- absolute/path-prefix forms;
- any value outside the characterized Webasyst app-id grammar.

Resolve/canonicalize paths and prove the final path remains inside the configured root. Pin symlink escape behavior explicitly.

- [ ] **Step 1: Write valid-path tests**

Pin ordinary app and `webasyst` manifest paths.

- [ ] **Step 2: Write traversal/symlink RED tests**

Include `../shop`, `shop/../../x`, backslashes, absolute forms and a symlink whose target leaves the root.

- [ ] **Step 3: Run RED**

```bash
python -m pytest tests/unit/test_application_registry_paths.py -v
```

Expected: FAIL.

- [ ] **Step 4: Implement minimal safe path service**

No file reading/parsing yet.

- [ ] **Step 5: Run GREEN**

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/gomazon_webasyst/compatibility/webasyst/application_registry/paths.py \
  tests/unit/test_application_registry_paths.py
git commit -m "feat: add safe webasyst application paths"
```

---

### Task 5: Normalize legacy apps.php and app.php into InstalledApplication

**Files:**
- Create: `src/gomazon_webasyst/compatibility/webasyst/application_registry/normalizer.py`
- Create: `src/gomazon_webasyst/compatibility/webasyst/application_registry/raw_config.py`
- Create: `tests/unit/test_application_registry_normalizer.py`
- Extend: `tests/compatibility/test_application_registry_source_characterization.py`

**Compatibility-private normalized inputs:**
Introduce explicit raw config records between parser and application Entity. They may represent parser-level absence/null internally, but MUST normalize all such states before returning `InstalledApplication`.

**Normalization pins:**
- apps enabled/disabled truth semantics exactly as characterized;
- configured order preserved;
- display name;
- vendor/version;
- scalar icon;
- size-keyed icon map;
- `img` fallback;
- header items;
- boolean true capability extraction;
- false capability omission;
- empty icon/header/capability collections are explicit immutable values;
- duplicate/invalid manifest structures fail deterministically;
- raw unknown non-boolean metadata is ignored unless a current consumer needs it.

Do not add OAuth's `webasyst` icon selection rule here.

- [ ] **Step 1: Write failing apps-config normalization tests**

Pin enabled/disabled ordering and exact 4.2.0 truth behavior from Task 0.

- [ ] **Step 2: Write failing manifest normalization tests**

Pin all icon/img/header/capability cases.

- [ ] **Step 3: Write malformed manifest tests**

Pin missing/invalid required metadata according to source characterization.

- [ ] **Step 4: Run RED**

```bash
python -m pytest \
  tests/unit/test_application_registry_normalizer.py \
  tests/compatibility/test_application_registry_source_characterization.py -v
```

Expected: FAIL.

- [ ] **Step 5: Implement pure normalizer**

No filesystem I/O and no OAuth/API imports.

- [ ] **Step 6: Run GREEN**

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/gomazon_webasyst/compatibility/webasyst/application_registry/normalizer.py \
  src/gomazon_webasyst/compatibility/webasyst/application_registry/raw_config.py \
  tests/unit/test_application_registry_normalizer.py \
  tests/compatibility/test_application_registry_source_characterization.py
git commit -m "feat: normalize legacy application metadata"
```

---

### Task 6: Filesystem discovery builds one immutable startup snapshot

**Files:**
- Create: `src/gomazon_webasyst/infrastructure/application_registry/filesystem_catalog.py`
- Modify: `src/gomazon_webasyst/composition/settings.py`
- Create: `tests/integration/test_application_registry_filesystem.py`
- Create: `tests/unit/test_application_registry_settings.py`

**Settings:**
Add typed `webasyst_root: Path`.

The root is a composition concern. Do not add filesystem paths to application contracts.

**Discovery responsibilities:**
1. read `wa-config/apps.php`;
2. parse configured ids;
3. apply characterized `webasyst` system-app inclusion;
4. resolve safe manifest paths;
5. parse manifests;
6. normalize entities;
7. construct immutable catalog snapshot.

Do not perform lazy per-request reads.

**Failure semantics:**
- missing root/apps config -> startup/configuration error according to characterization;
- file permission/I/O error -> infrastructure exception;
- parser/manifest corruption -> explicit compatibility configuration error;
- ordinary unknown app queried after construction -> typed `InstalledApplicationMissing`.

- [ ] **Step 1: Write temporary-root integration RED tests**

Build a minimal filesystem tree under `tmp_path`.

Pin:
- enabled app discovered;
- disabled app absent;
- `webasyst` behavior;
- snapshot order;
- app with missing manifest behavior exactly per Task 0.

- [ ] **Step 2: Write failure-semantics tests**

Malformed config must fail catalog construction, not create an empty catalog.

- [ ] **Step 3: Write settings tests**

Pin env parsing for `GOMAZON_WEBASYST_ROOT` and Path typing.

- [ ] **Step 4: Run RED**

```bash
python -m pytest \
  tests/integration/test_application_registry_filesystem.py \
  tests/unit/test_application_registry_settings.py -v
```

Expected: FAIL.

- [ ] **Step 5: Implement filesystem snapshot factory/catalog**

Prefer construction-time I/O followed by in-memory immutable lookup. Do not mix filesystem operations into `resolve()`.

- [ ] **Step 6: Run GREEN**

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/gomazon_webasyst/infrastructure/application_registry/filesystem_catalog.py \
  src/gomazon_webasyst/composition/settings.py \
  tests/integration/test_application_registry_filesystem.py \
  tests/unit/test_application_registry_settings.py
git commit -m "feat: discover installed webasyst applications"
```

---

### Task 7: Cut API Execution over to InstalledApplicationCatalog

**Files:**
- Modify: `src/gomazon_webasyst/application/api_execution/services/authorizer.py`
- Modify: `src/gomazon_webasyst/composition/api_execution.py`
- Modify: API Execution unit tests using `InstalledAppDirectory`
- Add/modify: `tests/unit/test_api_request_authorizer.py`
- Add/modify: `tests/unit/test_api_execution_container.py`

**Migration:**
- Replace `InstalledAppDirectory` dependency with `InstalledApplicationCatalog`.
- App existence authorization uses only resolved/missing result.
- No API code branches on app display metadata/capabilities.
- Do not change app-access/scope/license ordering.
- Do not register API methods from discovered manifests.

- [ ] **Step 1: Change tests first to canonical catalog fakes**

Existing tests should fail while production types still expect the old port.

- [ ] **Step 2: Pin authorization short-circuit order**

For a missing canonical app:
- app access is not called;
- scope/license are not reached;
- method registry is not reached by pipeline.

- [ ] **Step 3: Run RED**

Use the existing API execution focused suite plus new authorizer tests.

- [ ] **Step 4: Implement cutover**

Update constructor types/wiring only; preserve error code/payload behavior.

- [ ] **Step 5: Run GREEN + API compatibility suite**

```bash
python -m pytest \
  tests/unit/test_api_request_authorizer.py \
  tests/unit/test_api_execution_* \
  tests/compatibility/test_legacy_api_* \
  tests/integration/test_api_* -v
```

Adjust globs to existing filenames when executing.

- [ ] **Step 6: Commit**

```bash
git add src/gomazon_webasyst/application/api_execution/services/authorizer.py \
  src/gomazon_webasyst/composition/api_execution.py \
  tests
git commit -m "refactor: use canonical installed app catalog in api"
```

---

### Task 8: Catalog-backed OAuth consent projection and async lookup

**Files:**
- Create: `src/gomazon_webasyst/compatibility/webasyst/oauth/services/consent_application_projector.py`
- Replace or refactor: `src/gomazon_webasyst/infrastructure/oauth_authorization/app_catalog.py`
- Modify: `src/gomazon_webasyst/application/ports/oauth_consent_apps.py`
- Modify: `src/gomazon_webasyst/application/oauth_authorization/services/scope.py`
- Modify: `src/gomazon_webasyst/composition/oauth_authorization.py`
- Modify: `tests/unit/test_oauth_consent_catalog.py`
- Modify: `tests/unit/test_oauth_consent_scope_service.py`
- Create: `tests/unit/test_oauth_consent_application_projector.py`

**Interfaces:**
- Production OAuth catalog wraps `InstalledApplicationCatalog`.
- `OAuthConsentAppCatalog.resolve` becomes async.
- `OAuthConsentScopeService.filter` awaits lookup.
- Projector converts canonical Entity to existing `OAuthConsentApplication`.
- Webasyst-specific settings header icon selection is compatibility-only.

**Icon policy:**
Pin exact 4.2.0 behavior from Task 0:
- ordinary app preferred icon;
- `webasyst` settings header-item icon;
- deterministic fallback when expected icon metadata is absent, if legacy source defines one.

- [ ] **Step 1: Write projector RED tests**

Ordinary and `webasyst` cases.

- [ ] **Step 2: Convert catalog/scope tests to async canonical backing**

Pin requested order + silent missing/denied filtering exactly as before.

- [ ] **Step 3: Run RED**

```bash
python -m pytest \
  tests/unit/test_oauth_consent_application_projector.py \
  tests/unit/test_oauth_consent_catalog.py \
  tests/unit/test_oauth_consent_scope_service.py -v
```

Expected: FAIL.

- [ ] **Step 4: Implement projection/cutover**

Do not add filesystem I/O to OAuth packages.

- [ ] **Step 5: Run GREEN + OAuth suite**

```bash
python -m pytest \
  tests/unit/test_oauth_* \
  tests/compatibility/test_legacy_oauth_* \
  tests/integration/test_oauth_authorization_flow.py -v
```

- [ ] **Step 6: Commit**

```bash
git add src/gomazon_webasyst/compatibility/webasyst/oauth \
  src/gomazon_webasyst/infrastructure/oauth_authorization/app_catalog.py \
  src/gomazon_webasyst/application/ports/oauth_consent_apps.py \
  src/gomazon_webasyst/application/oauth_authorization/services/scope.py \
  src/gomazon_webasyst/composition/oauth_authorization.py \
  tests
git commit -m "refactor: project oauth consent from installed apps"
```

---

### Task 9: Share exactly one catalog instance in production composition

**Files:**
- Create: `src/gomazon_webasyst/composition/application_registry.py`
- Modify: `src/gomazon_webasyst/composition/container.py`
- Modify: `src/gomazon_webasyst/composition/api_execution.py`
- Modify: `src/gomazon_webasyst/composition/oauth_authorization.py`
- Modify/add: `tests/unit/test_application_registry_container.py`
- Modify: `tests/unit/test_oauth_authorization_container.py`
- Modify/add: container integration tests

**Target wiring:**

```text
Settings.webasyst_root
        |
        v
create_installed_application_catalog()
        |
        +----------------------+
        |                      |
        v                      v
API Execution          OAuth projection
```

**Requirements:**
- one constructed catalog object per Container;
- API and OAuth receive that same object (OAuth through wrapper/projector);
- test-oriented factory accepts an injected catalog so unrelated unit/integration tests do not need a real legacy tree;
- no separate production rediscovery;
- no default empty production catalog.

- [ ] **Step 1: Write identity-sharing RED test**

Assert the object referenced by API authorizer and OAuth projection ultimately points to the same canonical catalog instance.

- [ ] **Step 2: Write injection seam test**

Create container/components with `InMemoryInstalledApplicationCatalog` and no filesystem dependency.

- [ ] **Step 3: Run RED**

```bash
python -m pytest \
  tests/unit/test_application_registry_container.py \
  tests/unit/test_oauth_authorization_container.py -v
```

- [ ] **Step 4: Implement composition module and shared wiring**

Construct discovery before API/OAuth components.

- [ ] **Step 5: Run GREEN**

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/gomazon_webasyst/composition/application_registry.py \
  src/gomazon_webasyst/composition/container.py \
  src/gomazon_webasyst/composition/api_execution.py \
  src/gomazon_webasyst/composition/oauth_authorization.py \
  tests
git commit -m "feat: share installed app catalog in composition"
```

---

### Task 10: Cross-surface integration — one discovered app drives API and OAuth

**Files:**
- Create: `tests/integration/test_application_registry_cross_surface.py`
- Extend: `tests/integration/test_oauth_authorization_flow.py`
- Extend relevant API integration test

**Scenario:**
Create a temporary Webasyst-like root containing:
- `wa-config/apps.php`;
- one ordinary app manifest;
- the characterized `webasyst` manifest;
- no unrelated app.

Construct the same catalog/composition graph used by production.

Pin:
1. API authorizer sees the ordinary app as installed.
2. OAuth scope resolves the same app and metadata.
3. A disabled/nonconfigured app is missing to both.
4. A configured missing/corrupt manifest follows characterized startup behavior before either surface can diverge.
5. API method registry remains independent: installed app + missing method still gives `invalid_method`, not implicit execution.

- [ ] **Step 1: Write failing cross-surface test**

The test should demonstrate the old architecture would require two independent registrations.

- [ ] **Step 2: Run RED**

```bash
python -m pytest tests/integration/test_application_registry_cross_surface.py -v
```

- [ ] **Step 3: Make only minimal integration fixes**

Do not introduce new domain behavior merely to satisfy the integration test.

- [ ] **Step 4: Run GREEN**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_application_registry_cross_surface.py \
  tests/integration/test_oauth_authorization_flow.py \
  tests/integration
git commit -m "test: verify shared app catalog across api and oauth"
```

---

### Task 11: Remove obsolete app universes and add architecture guards

**Files:**
- Delete: `src/gomazon_webasyst/application/ports/installed_apps.py`
- Delete: `src/gomazon_webasyst/infrastructure/api_execution/app_directory.py`
- Remove production use of standalone empty `InMemoryOAuthConsentAppCatalog`
- Modify: `src/gomazon_webasyst/infrastructure/oauth_authorization/app_catalog.py` as needed
- Create: `tests/architecture/test_application_registry_boundaries.py`
- Modify: `tests/architecture/test_no_optional_result_contracts.py`
- Modify: `AGENTS.md`

**Architecture guards must assert:**
- no source import of old `InstalledAppDirectory`;
- no production construction of `InMemoryInstalledAppDirectory(frozenset())`;
- no production construction of an independent empty OAuth app catalog;
- application registry imports no compatibility/filesystem modules;
- parser package contains no execution/dynamic-import primitives;
- exactly one production canonical catalog construction path exists;
- `ApiMethodRegistry` and `DispatchRegistry` are still separate types;
- no `Optional` lookup result added.

- [ ] **Step 1: Write guards while obsolete files still exist**

Expected RED.

- [ ] **Step 2: Remove/migrate old imports and files**

Do not keep compatibility aliases merely to make dead architecture linger unless an external public contract truly requires them.

- [ ] **Step 3: Run targeted architecture suite**

```bash
python -m pytest \
  tests/architecture/test_application_registry_boundaries.py \
  tests/architecture/test_application_registry_taxonomy.py \
  tests/architecture/test_no_optional_result_contracts.py \
  tests/architecture/test_api_execution_* \
  tests/architecture/test_oauth_authorization_* -v
```

- [ ] **Step 4: Commit**

```bash
git add -A src/gomazon_webasyst tests/architecture AGENTS.md
git commit -m "refactor: remove duplicate installed app registries"
```

---

### Task 12: Full acceptance, documentation and completion record

**Files:**
- Modify: `docs/superpowers/plans/2026-09-19-installed-application-registry-discovery.md`
- Modify: `docs/superpowers/specs/2026-09-19-installed-application-registry-discovery-design.md` only if implementation discovered source-backed corrections
- Modify: `AGENTS.md`

- [ ] **Step 1: Run formatter/static checks configured by repository**

Use the repository's actual configured commands; do not invent a new toolchain.

- [ ] **Step 2: Run complete test suite**

```bash
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run focused acceptance again**

```bash
python -m pytest \
  tests/unit/test_installed_application_types.py \
  tests/unit/test_installed_application_catalog.py \
  tests/unit/test_legacy_php_config_parser.py \
  tests/unit/test_application_registry_paths.py \
  tests/unit/test_application_registry_normalizer.py \
  tests/integration/test_application_registry_filesystem.py \
  tests/integration/test_application_registry_cross_surface.py \
  tests/compatibility/test_application_registry_source_characterization.py \
  tests/architecture/test_application_registry_taxonomy.py \
  tests/architecture/test_application_registry_boundaries.py -v
```

Expected: PASS.

- [ ] **Step 4: Verify repository search has no obsolete production path**

Search for:
- `InstalledAppDirectory`;
- `InMemoryInstalledAppDirectory`;
- default empty `InMemoryOAuthConsentAppCatalog`;
- direct API/OAuth filesystem discovery;
- `eval(`, `exec(`, PHP subprocess invocation in application-registry parser.

Expected: no prohibited production matches.

- [ ] **Step 5: Verify runtime invariants manually from code**

Confirm:
- one catalog per Container;
- startup snapshot only;
- API/OAuth share it;
- OAuth projection owns its `webasyst` icon quirk;
- API method registry remains independent;
- malformed config cannot be mistaken for ordinary app lookup miss.

- [ ] **Step 6: Mark all plan checkboxes complete and update completion state in AGENTS.md**

Record the exact final test result count and any deliberately deferred behavior.

- [ ] **Step 7: Commit completion record**

```bash
git add docs/superpowers/plans/2026-09-19-installed-application-registry-discovery.md \
  docs/superpowers/specs/2026-09-19-installed-application-registry-discovery-design.md \
  AGENTS.md
git commit -m "docs: record installed application registry verification"
```

---

## Completion Definition

This plan is complete only when:

- production composition builds one canonical installed-app snapshot;
- API Execution and OAuth consent use that same snapshot;
- app identity/metadata comes from the configured Webasyst installation;
- exact ambiguous 4.2.0 behaviors are source-characterized;
- arbitrary PHP cannot execute;
- path traversal/root escape is prevented;
- no raw config/parser/path state leaks into application code;
- expected lookup miss remains typed and distinct from deployment/configuration faults;
- API method and dispatch registries remain independent;
- old API app directory and independent production OAuth app universe are gone;
- full CI is green.

## Follow-on

After merge, start a separate application runtime/capability registration slice. It may consume `InstalledApplicationCatalog` to explicitly register migrated app routing/API/plugin/event capabilities, but it MUST NOT reintroduce dynamic PHP class discovery or another installed-app source.
