# Installed Application Registry & Legacy Discovery — Design Specification

Status: implemented
Date: 2026-09-19
Repository: `boltholds/gomazon-webasyst`

## 1. Goal

Introduce one canonical runtime source of installed Webasyst applications and their normalized metadata, then make API Execution and OAuth consent consume projections of that source instead of maintaining independent empty registries.

This slice is intentionally narrower than installer migration, plugin/event discovery, bundled-app migration, or dynamic API-method discovery. It establishes the application identity/catalog boundary those later slices can depend on.

The result must preserve the accepted dependency direction:

```text
presentation / compatibility
          |
          v
      application
          |
          v
contracts + application-owned ports
          ^
          |
 infrastructure / compatibility implementations
```

The Python rewrite MUST NOT recreate `waSystem` as a global service locator.

## 2. Plan-vs-code gap audit

### 2.1 Existing API Execution app existence is only a test-oriented set

Current port:

- `src/gomazon_webasyst/application/ports/installed_apps.py`
- `InstalledAppDirectory.resolve(AppId) -> InstalledAppResolved | InstalledAppMissing`

Current infrastructure:

- `src/gomazon_webasyst/infrastructure/api_execution/app_directory.py`
- `InMemoryInstalledAppDirectory(frozenset[AppId])`

Current production composition:

- `create_default_api_execution_components()` always constructs `InMemoryInstalledAppDirectory(frozenset())`.

Consequences:

1. production API execution treats every ordinary application as not installed;
2. the directory carries no app metadata;
3. the source of installed identity is unrelated to Webasyst configuration;
4. the object is owned by the API Execution infrastructure package even though installed application identity is framework-wide.

### 2.2 OAuth consent maintains a second independent application catalog

Current port:

- `src/gomazon_webasyst/application/ports/oauth_consent_apps.py`
- `OAuthConsentAppCatalog.resolve(AppId)`

Current infrastructure:

- `src/gomazon_webasyst/infrastructure/oauth_authorization/app_catalog.py`
- `InMemoryOAuthConsentAppCatalog(tuple[OAuthConsentApplication, ...])`

Current production composition:

- `create_default_oauth_authorization_components()` always constructs `InMemoryOAuthConsentAppCatalog(())`.

Consequences:

1. production OAuth scope filtering drops every requested application;
2. OAuth duplicates application identity and presentation metadata independently from API app existence;
3. API and OAuth can disagree about whether the same `AppId` exists;
4. there is no canonical source for display name/icon metadata.

### 2.3 Composition allows drift between consumers

`composition/container.py` creates API Execution and OAuth Authorization separately. No shared installed-app dependency is built before them.

The accepted OAuth and API designs therefore have a deliberate temporary seam that is now due to be replaced: both slices can be correct in isolation while their application catalogs disagree.

### 2.4 Routing does not yet provide the missing registry

Routing compatibility currently normalizes supplied system/app route tables and produces typed settlements/dispatch. It does not discover installed applications from `wa-config/apps.php`, nor does it own app metadata.

The new catalog MUST remain separate from route parsing and `DispatchRegistry`. Routing may consume the catalog later, but route tables and handler registration are distinct responsibilities.

### 2.5 API method registration remains separate by design

`ApiMethodRegistry` is an explicit registry of Python `ApiMethodDefinition` entities. It replaces PHP request-to-class-name dynamic discovery.

The application catalog MUST NOT auto-import Python modules, construct handler class names, or register API methods implicitly. An application being installed does not imply that a Python API handler exists.

### 2.6 Settings have no Webasyst installation root

`composition/settings.py` currently has database/session/API settings only. There is no typed root path from which `wa-config/apps.php` and application manifests can be discovered.

### 2.7 ACL already declares this slice as deferred

`AGENTS.md` currently states that application installation/catalog validation is deferred until the application registry slice. This design closes that deferral without changing ACL semantics.

## 3. Legacy compatibility facts

The supplied Webasyst 4.2.0 source remains authoritative. Current public documentation/source may be used only as a structural cross-check when it agrees with the supplied source.

The compatibility behavior to preserve is:

1. `wa-config/apps.php` is the configured list of applications participating in runtime installation/discovery.
2. Enabled app ids are resolved to their application config under `wa-apps/<app_id>/lib/config/app.php`.
3. Application config contains presentation/runtime metadata such as `name`, `icon` or `img`, `version`, `vendor`, and boolean capability flags such as `frontend`, `rights`, `plugins`, `themes`, `auth`, and `csrf`.
4. The framework application `webasyst` is a special system identity and is available independently of an ordinary `wa-config/apps.php` entry.
5. `waSystem::appExists()` and `waSystem::getAppInfo()` observe the same loaded app set.
6. API method execution checks app existence before app access/scope/license/method resolution.
7. OAuth consent iterates requested scope order, drops missing or unauthorized apps, and obtains display metadata from application info.
8. OAuth consent has a Webasyst-specific icon behavior: for `webasyst`, the settings header-item icon is used.
9. Legacy config caching is an implementation optimization, not an application-domain concept.

Before implementation is declared compatible, exact edge behavior MUST be characterized against the supplied 4.2.0 archive for:

- a missing `wa-config/apps.php`;
- a configured app whose `lib/config/app.php` is missing;
- disabled/falsy app entries;
- `webasyst` discovery and manifest location;
- optional `build.php`;
- malformed/non-array config values;
- localization of app `name`;
- icon/`img` normalization;
- any 4.2.0-specific Installer auto-enable behavior.

Do not inherit a behavior only because it exists on a newer public branch.

### 3.1 Characterized 4.2.0 release snapshot

Task 0 is pinned to release commit `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5` (`Webasyst Framework v.4.2.0`, 2026-07-27). The detailed evidence record is `docs/superpowers/specs/2026-09-19-installed-application-registry-characterization.md`.

The characterized rules are now fixed:

- missing `wa-config/apps.php` is a configuration error (legacy exception code 600);
- `webasyst` is forcibly added to the configured set and its manifest is loaded from `wa-system/webasyst/lib/config/app.php`;
- configured falsey entries are disabled using PHP truth semantics;
- when `installer` is empty/disabled, legacy may force-enable it from truthy `webasyst/waid_credentials`;
- an enabled app with no `lib/config/app.php` is silently skipped;
- build metadata comes from `build.php` or debug-time/zero fallback, but current API/OAuth consumers do not use it;
- legacy discovery localizes app/header-item names and caches app info per locale;
- scalar icons, icon-size maps, `img` fallback and header-item paths are normalized during discovery;
- `webasyst` header item assets use the `wa-content/` prefix;
- malformed config is not an ordinary “app missing” state;
- legacy PHP `include` can execute code, but the Python compatibility parser intentionally rejects dynamic expressions.


## 4. Architectural decision

There is exactly one canonical application-owned port named `InstalledApplicationCatalog`.

It represents runtime-installed application identity and normalized metadata. API Execution, OAuth consent, future backend app menus, plugin/event discovery, and installer-facing operations may consume it or consumer-specific projections over it.

Consumer-specific registries remain valid where they represent a different concept:

- `ApiMethodRegistry` — registered executable Python API methods;
- `DispatchRegistry` — registered dispatch handlers/plugins;
- `OAuthConsentAppCatalog` — OAuth-specific projection contract, backed by the canonical installed-app catalog in production.

The canonical catalog MUST NOT become a service locator. It returns application entities/metadata only; it does not return routers, repositories, sessions, handlers, plugin instances, or arbitrary services.

## 5. Taxonomy

All new application-registry domain/application types must be classifiable as Entity, VO, Service, or Composite.

### 5.1 Entity — InstalledApplication

`InstalledApplication` has stable identity `AppId`.

Conceptual shape:

```python
@dataclass(slots=True, frozen=True)
class InstalledApplication:
    app_id: AppId
    display_name: ApplicationDisplayName
    icons: ApplicationIconSet
    vendor: ApplicationVendor
    version: ApplicationVersion
    capabilities: ApplicationCapabilities
    header_items: ApplicationHeaderItems
```

The entity is a normalized runtime projection, not a lossless AST of `app.php`.

`ApplicationDisplayName` is locale-neutral in this slice: it contains the manifest's default/raw name. Webasyst 4.2.0 localized app names while building its per-locale cache, but a single shared Python catalog must not capture the locale of whichever request/user happened to initialize it. Locale-specific display projection is deferred to the localization/application-presentation slice. OAuth therefore uses the raw manifest name until that projection exists and MUST NOT claim localized consent-screen parity yet.

Legacy `build` is also excluded from the first Entity because it is runtime/cache-busting metadata and no current API/OAuth consumer needs it.

Fields are non-nullable. Absence that is semantically allowed is represented by value objects with explicit empty collections or explicit variants, not `None`.

### 5.2 Value Objects

Required open immutable VOs:

- `ApplicationDisplayName(value: str)`
- `ApplicationVendor(value: str)`
- `ApplicationVersion(value: str)`
- `ApplicationIconReference(value: str)`
- `ApplicationHeaderItemId(value: str)`
- `ApplicationCapabilityName(value: str)`

Required immutable collection VOs:

- `ApplicationIcon(size: int, reference: ApplicationIconReference)`
- `ApplicationIconSet(items: tuple[ApplicationIcon, ...])`
- `ApplicationCapabilities(values: frozenset[ApplicationCapabilityName])`
- `ApplicationHeaderItem(item_id, display_name, icons)`
- `ApplicationHeaderItems(items: tuple[ApplicationHeaderItem, ...])`

Capability names remain open identifiers. Third-party applications may expose additional boolean capabilities, so they MUST NOT be forced into a closed `EnumStr`.

Closed lookup/discovery/result discriminators derive from `EnumStr`.

### 5.3 Services

Application services are limited to domain projections/rules, for example:

- `InstalledApplicationExistenceService` only if a consumer needs an existence-only facade;
- `OAuthConsentApplicationProjector` converts one canonical `InstalledApplication` into the existing OAuth `OAuthConsentApplication` entity;
- `ApplicationIconSelectionService` selects a preferred icon without filesystem I/O.

The Webasyst-specific `webasyst -> header_items.settings.icon` OAuth rule belongs to a compatibility projector/service, not the canonical entity.

### 5.4 Composites

No long-running runtime/service-locator object is introduced.

If orchestration is required, a Composite may assemble a discovery snapshot from already-normalized config records, but it MUST NOT expose unrelated services by app id.

## 6. Canonical application-owned port

Create:

`src/gomazon_webasyst/application/ports/installed_application_catalog.py`

Conceptual contract:

```python
@dataclass(slots=True, frozen=True)
class InstalledApplicationResolved:
    application: InstalledApplication

@dataclass(slots=True, frozen=True)
class InstalledApplicationMissing:
    app_id: AppId

InstalledApplicationResolution = (
    InstalledApplicationResolved | InstalledApplicationMissing
)

@dataclass(slots=True, frozen=True)
class InstalledApplicationSnapshot:
    applications: tuple[InstalledApplication, ...]

class InstalledApplicationCatalog(Protocol):
    async def resolve(self, app_id: AppId) -> InstalledApplicationResolution: ...
    async def snapshot(self) -> InstalledApplicationSnapshot: ...
```

Rules:

- lookup miss is explicit, never `None`;
- snapshot order follows normalized legacy configured-app order;
- duplicate `AppId` is invalid catalog construction;
- returned entities/VOs are immutable;
- callers cannot mutate catalog state;
- no filesystem path or parser token leaks through this port.

The old `InstalledAppDirectory` is superseded. It may exist temporarily as a migration adapter during TDD, but it is removed before the slice is marked complete.

## 7. Legacy discovery adapter

Create a Webasyst compatibility/infrastructure adapter outside application code.

Suggested packages:

```text
compatibility/webasyst/application_registry/
  config_parser.py
  normalizer.py
  paths.py

infrastructure/application_registry/
  filesystem_catalog.py
  in_memory_catalog.py
```

### 7.1 Root path

Add a typed composition setting:

```python
webasyst_root: Path
```

The filesystem adapter derives legacy paths from this root. Application contracts never receive `Path`.

Tests that do not exercise legacy discovery inject `InMemoryInstalledApplicationCatalog` through composition helpers rather than depending on the developer machine filesystem.

### 7.2 Config source

The adapter reads:

- `<root>/wa-config/apps.php`;
- `<root>/wa-apps/<app_id>/lib/config/app.php`;
- `<root>/wa-system/webasyst/lib/config/app.php` for the framework app;
- optional build metadata only if characterization proves it is required by a current consumer.

### 7.3 PHP configuration parsing safety

The Python service MUST NOT:

- `eval` PHP;
- execute arbitrary application config code;
- spawn PHP just to load config;
- import code based on request/application strings.

The first parser supports the declarative subset required by the supplied 4.2.0 configs:

- `return array(...)`;
- `return [...]`;
- string keys/values;
- integers/floats;
- booleans;
- null only inside the raw compatibility parser when present in legacy input;
- nested arrays;
- comments and trailing commas.

The parser immediately normalizes raw null/absence into explicit typed values before crossing the compatibility boundary.

A config expression outside the supported declarative subset produces an explicit compatibility/configuration failure. It is never silently executed.

### 7.4 Manifest normalization

Normalization owns legacy rules such as:

- validating/sanitizing `AppId`;
- choosing source paths;
- `icon` scalar versus icon-size map;
- `img` fallback;
- normalizing icon references relative to the framework root where required;
- extracting boolean capability keys into `ApplicationCapabilities`;
- normalizing header items needed by current consumers;
- preserving configured-app order.
- applying characterized PHP truth semantics to enabled/disabled entries;
- reproducing the optional WAID Installer auto-enable rule through an injected compatibility settings/policy seam;
- keeping canonical names locale-neutral rather than embedding a per-user locale in the shared snapshot;
- omitting legacy build/cache metadata until a concrete consumer requires it.

Raw PHP dictionaries do not cross into application code.

## 8. Production catalog lifecycle

The first implementation uses one immutable discovery snapshot per application container.

Reasons:

- current Python composition already constructs long-lived registries at startup;
- it avoids blocking filesystem reads in request execution;
- it gives API and OAuth the same consistent view;
- it keeps installer mutation/hot reload outside this slice.

If application installation/config changes while the Python process is running, a restart is required in this first slice.

A later Installer/runtime-refresh slice may introduce an atomic snapshot reload mechanism behind the same `InstalledApplicationCatalog` port without changing API/OAuth use cases.

Do not introduce request-time mtime polling in this slice.

## 9. API Execution integration

`ApiRequestAuthorizer` changes from `InstalledAppDirectory` to `InstalledApplicationCatalog`.

Its observable order remains unchanged:

```text
credential
-> activity touch
-> installed application
-> app access
-> token scope
-> license
-> method registry
-> HTTP method validation
-> handler
```

For app existence, the authorizer only inspects resolved/missing state. It MUST NOT branch on display metadata or capabilities.

`InMemoryInstalledAppDirectory` is removed from default production composition.

`ApiMethodRegistry` remains independent and may still be empty until explicit methods are registered.

## 10. OAuth consent integration

The existing OAuth domain contract remains useful because consent presentation is consumer-specific.

Production `OAuthConsentAppCatalog` becomes a catalog-backed projection:

```text
InstalledApplicationCatalog
        |
        v
LegacyOAuthConsentApplicationProjector
        |
        v
OAuthConsentApplication
```

Rules:

- scope order is the original requested order;
- missing canonical apps are omitted;
- access policy runs after successful catalog resolution;
- denied apps are omitted;
- ordinary app display name/icons come from normalized installed metadata;
- ordinary app name is the locale-neutral manifest default until a separate localization projection is implemented;
- `webasyst` uses the characterized settings header-item icon rule;
- the projector contains no filesystem I/O.

Because the canonical catalog lookup is async, `OAuthConsentAppCatalog.resolve` becomes async and `OAuthConsentScopeService.filter()` awaits it.

The old standalone `InMemoryOAuthConsentAppCatalog` remains only as a unit-test fake if useful; production default MUST NOT create an independent empty OAuth app universe.

## 11. Composition

`create_container...` constructs exactly one installed application catalog and shares it.

Target wiring:

```text
Settings.webasyst_root
        |
        v
Legacy filesystem/config discovery
        |
        v
InstalledApplicationCatalog
       / \
      /   \
     v     v
API Execution     OAuth consent projection
```

Add a composition seam for tests:

```python
create_container_with_application_catalog(
    settings,
    *,
    installed_applications: InstalledApplicationCatalog,
    ...
)
```

or fold the catalog into the existing explicit test-oriented container factory.

There MUST NOT be separate production calls that independently rediscover applications for API and OAuth.

## 12. Error and startup policy

The distinction is:

- expected app lookup miss -> typed `InstalledApplicationMissing`;
- invalid/missing runtime installation configuration -> startup/configuration error;
- filesystem permission/I/O failure -> infrastructure exception;
- malformed unsupported PHP config -> compatibility/configuration error.

Do not collapse configuration corruption into “app missing,” because that hides deployment faults and can produce inconsistent authorization behavior.

Exact behavior for a configured app with a missing manifest is source-characterized. If 4.2.0 skips it, the compatibility discovery adapter may omit that app while still reporting diagnostics; if the supplied source differs, the supplied source wins.

## 13. Security constraints

Application discovery is a trust boundary.

Required rules:

1. `AppId` must not permit path traversal.
2. All derived application paths remain under the configured Webasyst root.
3. Symlink/path escape behavior must be explicitly tested.
4. No arbitrary PHP execution.
5. No request parameter may select a filesystem path.
6. No request parameter may turn into a Python module/class import.
7. Parsed config size/depth must be bounded to prevent pathological input from exhausting the process.
8. Duplicate ids and structurally invalid manifests are rejected deterministically.

## 14. What remains separate

This slice does NOT implement:

- Installer install/update/delete;
- live catalog hot reload;
- plugin discovery/activation;
- event discovery;
- cron discovery;
- CLI command discovery;
- bundled application migration;
- automatic Python API-method registration from legacy PHP classes;
- automatic routing-table loading;
- template/theme discovery;
- license-state discovery;
- Webasyst ID/social auth;
- arbitrary PHP config execution;
- localization engine migration.

It creates the stable installed-application seam those slices can consume.

## 15. TDD/characterization requirements

### 15.1 Compatibility characterization

Add fixtures from the supplied 4.2.0 source for:

- simple `apps.php` enabled/disabled entries;
- missing apps config;
- app manifest missing;
- scalar `icon`;
- icon-size map;
- `img` fallback;
- nested `header_items`;
- `webasyst` special manifest;
- boolean capabilities;
- both `array(...)` and `[...]` syntax;
- comments/trailing commas;
- unsupported dynamic expression.

### 15.2 Unit

Cover:

- immutable VOs/entity;
- duplicate catalog ids;
- explicit resolve miss;
- order-preserving snapshot;
- capability extraction;
- icon normalization/selection;
- OAuth projection including `webasyst` icon behavior.

### 15.3 Architecture

Enforce:

- application registry imports no FastAPI/Starlette/SQLAlchemy;
- application code imports no PHP parser/filesystem adapter;
- compatibility parser does not expose raw dictionaries into application;
- no `Optional`/sentinel lookup results;
- API and OAuth production composition share one catalog instance;
- no default empty production app directory/catalog remains.

### 15.4 Integration

Use a temporary Webasyst-like root tree and assert:

1. `wa-config/apps.php` + app manifests produce a canonical snapshot;
2. API authorization recognizes a discovered app;
3. OAuth consent resolves the same app and metadata;
4. an app removed/disabled before container construction is absent to both consumers;
5. malformed config fails composition rather than producing divergent catalogs.

## 16. Migration sequence

1. Add Entity/VO/contracts and `InstalledApplicationCatalog` port with tests.
2. Add in-memory canonical catalog for unit tests.
3. Add restricted legacy PHP return-array parser with source-backed fixtures.
4. Add path resolver + manifest normalizer.
5. Add filesystem discovery and startup snapshot.
6. Migrate API Execution from `InstalledAppDirectory`.
7. Add catalog-backed OAuth consent projection and migrate async lookup.
8. Wire one shared catalog in `Container`.
9. Add cross-surface integration tests.
10. Remove production empty app catalogs/directories.
11. Update architecture guards and completion documentation.

## 17. Acceptance criteria

The slice is complete when all of the following are true:

- one canonical `InstalledApplicationCatalog` is constructed in production composition;
- API Execution and OAuth consent observe the same installed app set;
- the catalog is sourced from the configured Webasyst installation rather than hardcoded empty sets;
- `webasyst` system identity and OAuth icon behavior match characterized 4.2.0 behavior;
- no arbitrary PHP is executed;
- raw PHP config maps do not enter application code;
- API method and dispatch registries remain separate;
- expected lookup misses are typed;
- configuration corruption remains exceptional/diagnostic;
- full CI is green;
- `AGENTS.md` records the boundary.

## 18. Follow-on slice

After this registry is merged, the next high-value vertical slice is application capability/runtime registration:

- use the canonical app catalog as input;
- explicitly register Python routing/API/plugin/event capabilities per migrated application;
- migrate the first real bundled application/API method without dynamic class-name discovery.

That follow-on work must consume this catalog rather than inventing another installed-app source.
