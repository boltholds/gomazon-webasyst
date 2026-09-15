# Static Application Registry Design

**Date:** 2026-09-15  
**Status:** accepted in chat; written spec pending user review  
**Scope:** read-only application/plugin catalog and installation registry for the Python Webasyst 4.2.0 rewrite

## 1. Goal

Introduce one framework-wide, typed, read-only source of truth for:

- which bundled Webasyst 4.2.0 applications are known to this Python implementation;
- which application-owned bundled plugins are known and which application owns them;
- which known applications/plugins are enabled for a concrete installation;
- normalized application/plugin metadata needed by framework consumers;
- validation of application/plugin availability for ACL writes and dispatch.

The subsystem MUST NOT parse or execute PHP at runtime. Bundled `app.php` and application-owned `plugin.php` metadata from the supplied Webasyst Framework 4.2.0 source are copied once into typed Python descriptors and are canonical for this rewrite.

This slice is read-only. Installing, enabling, disabling, updating, uninstalling, or persisting installation state is explicitly deferred.

## 2. Authoritative legacy behavior

The supplied Webasyst Framework 4.2.0 source is authoritative under ADR-015.

Relevant legacy behavior:

- `waSystem::getApps()` reads `wa-config/apps.php`, force-adds `webasyst`, then loads metadata from each enabled application's `lib/config/app.php`.
- The bundled `wa-config/apps.php.example` enables `team`, `site`, `blog`, and `photos`; `webasyst` is supplied by framework logic rather than that file.
- `waSystem::getApps(false)` hides `webasyst` from the ordinary application list; `getApps(true)` includes it.
- `waAppConfig::getPlugins()` reads the application's configured plugin enablement state, then loads each enabled plugin's `plugins/<plugin>/lib/config/plugin.php`.
- Plugin metadata is enriched by legacy framework behavior: application/plugin identity is attached, image paths are normalized, `rights` may imply a `rights.config` handler, `frontend` may imply a `routing` handler, and app-specific settings flags may normalize to `custom_settings`.
- Plugin ownership is application-scoped. A plugin id is not a framework-global id.

The exact supplied 4.2.0 archive contains the framework `webasyst` application descriptor plus nine bundled `wa-apps` application descriptors:

- `webasyst` (framework system application)
- `apiexplorer`
- `blog`
- `developer`
- `dummy`
- `installer`
- `photos`
- `site`
- `team`
- `ui`

It also contains 21 application-owned bundled plugin descriptors:

- `blog/akismet`
- `blog/category`
- `blog/emailsubscription`
- `blog/favorite`
- `blog/gravatar`
- `blog/import`
- `blog/markdown`
- `blog/myposts`
- `blog/tag`
- `blog/troll`
- `photos/comments`
- `photos/imageeffects`
- `photos/import`
- `photos/publicgallery`
- `photos/watermark`
- `site/exampleblock`
- `site/rublesign`
- `team/caldav`
- `team/googlecalendar`
- `team/ics`
- `team/office365`

Framework service plugins under `wa-plugins/payment`, `wa-plugins/shipping`, `wa-plugins/sms`, and similar service-plugin families are not application-owned plugins and are outside this slice.

## 3. Non-goals

This slice does not implement:

- PHP config parsing;
- PHP execution/subprocesses;
- filesystem application discovery;
- dynamic application installation or removal;
- dynamic plugin installation or removal;
- enable/disable mutation;
- writing `wa-config/apps.php` or app plugin config files;
- installer/update marketplace behavior;
- WAID-driven dynamic force-enabling of Installer;
- payment/shipping/sms service-plugin registries;
- plugin event execution;
- rights-config rendering;
- application administration HTTP APIs;
- application-management UI;
- installation-state cache invalidation.

## 4. Architectural split

The subsystem has three distinct concepts:

```text
StaticWebasyst42Catalog
          +
InstallationManifest
          |
          v
StaticApplicationRegistry
```

### 4.1 Static catalog

The catalog describes what this Python implementation knows how to represent.

It is immutable application/plugin metadata copied from the exact bundled Webasyst 4.2.0 source.

It does not represent whether an application/plugin is enabled in a concrete installation.

### 4.2 Installation manifest

The manifest describes the ordered enabled state for one installation.

It contains identities only, not duplicated metadata.

### 4.3 Application registry

The registry combines catalog knowledge with installation state and exposes typed resolution results to framework consumers.

The registry is the framework-wide source of application/plugin availability. Consumers must not maintain parallel enabled-app/plugin sets.

## 5. Shared identifiers

`AppId` is no longer ACL-specific. It is used by access control, dispatch, application registry, and future event/plugin subsystems.

Move shared application identifiers into a framework-wide application value module, for example:

```text
src/gomazon_webasyst/application/app_values.py
```

Internal immutable value objects:

```python
@dataclass(slots=True, frozen=True)
class AppId:
    value: str

@dataclass(slots=True, frozen=True)
class PluginId:
    value: str

@dataclass(slots=True, frozen=True)
class PluginRef:
    app_id: AppId
    plugin_id: PluginId
```

`PluginRef` is required because plugin ids are scoped to their owner application.

The existing ACL import surface may temporarily re-export `AppId` from `access_values.py` during migration, but there MUST be only one concrete `AppId` type.

## 6. Typed application descriptors

Cross-boundary descriptors use Pydantic v2. No canonical `dict[str, Any]`, `extra`, or opaque metadata bags are allowed.

The descriptor shape is normalized around framework semantics rather than mechanically reproducing PHP associative arrays.

Conceptually:

```text
ApplicationDescriptor
├── identity
├── presentation
├── capabilities
└── framework metadata
```

The concrete contract contains at least:

- `id: AppId` (serialized through a Pydantic-friendly representation)
- name
- version
- vendor
- icon/presentation information where present
- description where present
- normalized UI-version support
- normalized forced-UI behavior where present
- normalized capability flags
- routing parameters
- header items
- framework prefix/critical-version fields where present

### 6.1 Capabilities

Known bundled 4.2.0 capability flags are represented explicitly rather than as arbitrary metadata. Examples include:

- `frontend`
- `rights`
- `plugins`
- `auth`
- `themes`
- `pages`
- `mobile`
- `csrf`
- `my_account`
- `system`

Absent legacy boolean capability flags normalize to `False`; they do not become nullable fields.

### 6.2 UI versions

Legacy values such as `"1.3,2.0"` are normalized into a closed typed UI-version collection.

The descriptor must not require consumers to parse comma-delimited legacy strings.

### 6.3 Routing parameters

Routing metadata remains extensible but typed:

```python
ConfigScalar = str | int | bool

@dataclass(slots=True, frozen=True)
class ApplicationRoutingParameter:
    name: str
    value: ConfigScalar
```

The descriptor exposes an ordered tuple of routing parameters. No `Any` value is accepted.

### 6.4 Header items

Header items are normalized into explicit descriptors containing stable identity, name, icon/image metadata, link, and a typed access requirement.

Access requirement uses explicit variants, for example:

```text
PublicHeaderItem
RequiresRight(RightName)
```

No nullable access-control bag is used.

## 7. Typed plugin descriptors

Application-owned plugin metadata is represented by `PluginDescriptor` and owned by `PluginRef`.

The concrete descriptor contains at least:

- `ref: PluginRef`
- name
- description where present
- version
- vendor
- presentation/image metadata where present
- normalized plugin capabilities
- normalized integration metadata
- normalized event handler descriptors

### 7.1 Plugin capabilities

Only actual bundled 4.2.0 capabilities are modeled in this slice. Examples include:

- `frontend`
- `rights`
- `custom_settings`
- `site_settings`
- `photos_settings`
- `external_calendar`

Capabilities are explicit typed fields, not an arbitrary dictionary.

### 7.2 Plugin integration variants

Correlated integration state must be structural. For example Team external-calendar plugins must not be representable as `external_calendar=False` with a non-empty integration level.

Use a variant family such as:

```text
NoPluginIntegration
ExternalCalendarIntegration(level)
```

with a closed integration-level enum containing actual bundled values such as `FULL` and `SUBSCRIPTION`.

### 7.3 Event handlers

Legacy plugin `handlers` are normalized into explicit handler descriptors.

Two important shapes exist in bundled 4.2.0:

```text
OwnedAppHandler
├── event
└── method

CrossApplicationHandler
├── event_app_id
├── event
├── class_name
└── method
```

The second form covers the special cross-application handler declarations such as Site Rublesign.

The catalog describes handler metadata only. Executing plugin events is deferred.

### 7.4 Legacy derived handlers

Characterization must include legacy derived-handler semantics from `waAppConfig::getPlugins()`:

- a plugin with `rights=true` effectively has a `rights.config -> rightsConfig` handler unless explicitly present;
- a plugin with `frontend=true` effectively has a `routing -> routing` handler unless explicitly present;
- application-specific settings capability may normalize to `custom_settings`.

The static descriptor SHOULD represent the normalized effective metadata that framework consumers would observe, not require each consumer to reimplement these rules.

## 8. Static catalog layout

Do not create one giant hand-maintained dictionary.

Recommended layout:

```text
compatibility/webasyst/applications/
  catalog.py
  descriptors/
    webasyst.py
    apiexplorer.py
    blog.py
    developer.py
    dummy.py
    installer.py
    photos.py
    site.py
    team.py
    ui.py
  plugins/
    blog.py
    photos.py
    site.py
    team.py
```

Each descriptor module contains immutable typed constants copied from the 4.2.0 source.

`catalog.py` only assembles and validates them:

```python
WEBASYST_42_CATALOG = ApplicationCatalog(
    applications=(...),
    plugins=(...),
)
```

Catalog construction rejects duplicate application ids and duplicate plugin refs as configuration/programming errors.

## 9. Installation manifest

Installation order has observable UI/framework meaning in legacy Webasyst, so enabled state must remain ordered.

Use a structural manifest:

```python
@dataclass(slots=True, frozen=True)
class InstalledApplication:
    app_id: AppId
    plugins: tuple[PluginId, ...]

@dataclass(slots=True, frozen=True)
class InstallationManifest:
    apps: tuple[InstalledApplication, ...]
```

This shape makes plugin ownership explicit and structurally prevents a plugin from being enabled independently of an installed owner application.

### 9.1 Manifest invariants

Registry construction rejects:

- duplicate installed applications;
- duplicate plugins within an installed application;
- an installed application unknown to the catalog;
- an installed plugin unknown to the catalog;
- a plugin listed beneath an application other than its catalog owner.

These are startup/configuration failures. They are not ordinary typed lookup misses.

### 9.2 `webasyst` system application

Legacy `waSystem::getApps()` force-adds `webasyst` independently of `wa-config/apps.php`.

The Python installation model therefore requires the `webasyst` application to be present in a valid runtime installation manifest. It remains identifiable as a system/global-control application through compatibility semantics.

The registry may provide ordinary and system-inclusive listing operations to mirror the useful distinction in `getApps(false)` versus `getApps(true)` without reproducing PHP method signatures.

### 9.3 Default bundled profile

If this slice supplies a default example/composition manifest, it should mirror the supplied `wa-config/apps.php.example` plus the framework-required `webasyst` application:

1. `webasyst`
2. `team`
3. `site`
4. `blog`
5. `photos`

No bundled app-owned plugins are implicitly enabled by that default profile because the supplied archive does not provide an equivalent plugin-enable config example. Tests and product composition may inject explicit manifests.

The legacy WAID behavior that may force-enable `installer` is deferred because this static read-only slice has no live Webasyst settings source for that condition.

## 10. Application registry result model

Expected resolution state is explicit and never encoded as `None` or bool.

### 10.1 Applications

```text
ApplicationResolution
├── ApplicationEnabled(descriptor)
├── ApplicationDisabled(descriptor)
└── ApplicationUnknown(app_id)
```

`Disabled` means known to the catalog but absent from this installation manifest.

`Unknown` means not present in the catalog.

### 10.2 Plugins

```text
PluginResolution
├── PluginEnabled(descriptor)
├── PluginDisabled(descriptor)
├── PluginOwnerDisabled(descriptor, owner)
└── PluginUnknown(plugin_ref)
```

A known plugin whose owner app is disabled resolves as `PluginOwnerDisabled`.

A known plugin whose owner app is enabled but which is not listed in that installed app's plugin list resolves as `PluginDisabled`.

### 10.3 Registry port

Application-owned port, conceptually:

```python
class ApplicationRegistry(Protocol):
    def resolve_app(self, app_id: AppId) -> ApplicationResolution: ...
    def resolve_plugin(self, plugin: PluginRef) -> PluginResolution: ...
    def list_apps(self) -> tuple[ApplicationDescriptor, ...]: ...
    def list_enabled_apps(self) -> tuple[ApplicationDescriptor, ...]: ...
    def list_plugins(self, app_id: AppId) -> PluginListResult: ...
    def list_enabled_plugins(self, app_id: AppId) -> PluginListResult: ...
```

Canonical availability APIs do not return bool. Consumers branch on typed resolution variants.

Listing an unknown app uses an explicit typed list rejection/result rather than an empty tuple that could be confused with a known app with no plugins.

## 11. Implementation name

The production implementation is intentionally static and should be named accordingly:

```text
StaticApplicationRegistry
StaticWebasyst42Catalog
```

Do not call it `InMemoryApplicationRegistry`; static catalog composition is the intended production architecture for bundled 4.2.0 metadata, not a temporary test implementation.

Tests may use `FakeApplicationRegistry`.

## 12. ACL integration

The existing ACL evaluator/read path remains registry-independent.

This is deliberate: existing `wa_contact_rights` rows for an unknown or currently disabled app remain readable as legacy data. Registry state must not silently erase or filter persisted compatibility data.

Registry validation is added only to new app-scoped mutations:

- `AssignRight`
- `RevokeRight`
- `SetAppAccess`

Mutation sequence becomes:

```text
authorize actor
    -> validate access target
    -> resolve app in ApplicationRegistry
    -> require ApplicationEnabled
    -> build legacy mutation plan
    -> execute/write
    -> commit
```

Add explicit ACL mutation rejection reasons:

```text
APPLICATION_NOT_FOUND
APPLICATION_DISABLED
```

For `AssignRight` and `RevokeRight`, the permission key's `app_id` is validated.

For `SetAppAccess`, the supplied app id is validated before planning.

`SetGlobalAdminAccess` does not receive an app id and continues to use Webasyst global-control semantics internally, so it does not need generic application resolution as a request validation step.

The registry does not move into `RightsEvaluator` and does not alter numeric ACL evaluation semantics.

## 13. Dispatch integration

Current dispatch combines handler registration and plugin availability in one `DispatchRegistry`. These responsibilities must be split.

### 13.1 Handler registry

Application-owned `HandlerRegistry` contains only Python handler resolution:

```python
class HandlerRegistry(Protocol):
    def controller_id(...): ...
    def action_id(...): ...
    def actions_id(...): ...
```

The current in-memory implementation loses its plugin-enabled set and `enable_plugin()` installation-state API.

### 13.2 Resolver dependencies

`DispatchResolver` receives both:

```text
HandlerRegistry
ApplicationRegistry
```

Application namespace flow:

```text
request app
    -> resolve_app
    -> require ApplicationEnabled
    -> handler lookup
```

Plugin namespace flow:

```text
PluginRef(app, plugin)
    -> resolve_plugin
    -> require PluginEnabled
    -> handler lookup
```

This explicitly distinguishes:

- unknown application/plugin;
- disabled application/plugin;
- enabled application/plugin with no registered Python handler.

The last case remains a dispatch-target-not-found problem rather than being misreported as installation-disabled.

Dispatch-specific presentation/compatibility exceptions may map typed registry results to existing `PluginUnavailable`/application-unavailable errors, but the registry itself stays exception-free for ordinary lookup outcomes.

## 14. Composition

Composition builds exactly one registry instance from:

```text
WEBASYST_42_CATALOG
+
InstallationManifest
```

The same instance is injected into:

- ACL app-scoped mutation use cases;
- dispatch resolver;
- future event/plugin framework consumers.

Application code depends only on the application-owned registry port/contracts. It MUST NOT import the concrete Webasyst catalog.

Concrete catalog and installation-profile selection belong at the composition/compatibility edge.

## 15. Error model

Ordinary runtime state uses typed results:

- unknown app/plugin;
- disabled app/plugin;
- owner-disabled plugin;
- plugin-list request for unknown app.

Invalid static catalog or installation manifest is a startup/configuration/programming failure and may raise a dedicated configuration exception during registry construction.

Infrastructure failures are not relevant to the first static implementation because no I/O is performed by the registry.

## 16. Characterization strategy

No runtime parser is required, but the manually copied catalog still needs source-backed protection.

Characterization tests pin the bundled 4.2.0 inventory and normalized effective metadata.

At minimum they verify:

- exact bundled application ids, including system `webasyst`;
- exact 21 application-owned bundled plugin refs;
- representative identity/version/vendor/name fields;
- application capabilities;
- UI-version normalization;
- routing parameter normalization;
- header-item normalization;
- plugin capability normalization;
- Team external-calendar integration variants;
- owned and cross-application handler normalization;
- derived `rights.config` and `routing` handler semantics where applicable;
- the supplied default app profile semantics (`webasyst` + apps enabled in `apps.php.example`).

These tests are the migration guard against accidental drift from the supplied 4.2.0 source.

## 17. Unit tests

Unit coverage includes:

- `AppId`, `PluginId`, `PluginRef` value semantics;
- only one concrete `AppId` type exists;
- descriptor validation/serialization;
- catalog uniqueness validation;
- manifest ordering;
- manifest invariant failures;
- enabled/disabled/unknown application resolution;
- enabled/disabled/owner-disabled/unknown plugin resolution;
- plugin listing typed results;
- system-inclusive versus ordinary app listing where exposed.

## 18. Integration tests

### 18.1 ACL

Verify:

- assigning a right for an unknown app returns `APPLICATION_NOT_FOUND` and does not write;
- assigning/access mutation for a disabled known app returns `APPLICATION_DISABLED` and does not write;
- enabled app mutation succeeds;
- legacy read/evaluation of a persisted unknown app id still works;
- ACL evaluator remains unchanged and registry-independent.

### 18.2 Dispatch

Verify:

- unknown/disabled application cannot dispatch;
- unknown/disabled plugin cannot dispatch;
- enabled plugin with missing handler produces dispatch-target-not-found;
- enabled plugin with registered handler resolves normally;
- plugin availability no longer depends on handler-registry state.

### 18.3 Composition

Verify the same `ApplicationRegistry` instance is injected into ACL write-side validation and dispatch.

## 19. Architecture guards

Add guards that enforce:

- no PHP parser/runtime/subprocess dependency in registry code;
- no `dict[str, Any]` or equivalent opaque canonical descriptor bag;
- exactly one shared `AppId` implementation;
- application/contracts do not import the concrete Webasyst catalog;
- ACL evaluator/read math does not depend on `ApplicationRegistry`;
- app-scoped ACL writes do depend on the registry port;
- handler registry no longer owns application/plugin installation state;
- expected registry lookup results do not use `Optional`, `None`, bool, or empty-container sentinels.

## 20. Proposed package layout

```text
src/gomazon_webasyst/
  application/
    app_values.py
    application_registry.py
    ports/
      application_registry.py
      handler_registry.py

  contracts/
    applications.py
    enums.py

  compatibility/
    webasyst/
      applications/
        catalog.py
        registry.py
        descriptors/
          webasyst.py
          apiexplorer.py
          blog.py
          developer.py
          dummy.py
          installer.py
          photos.py
          site.py
          team.py
          ui.py
        plugins/
          blog.py
          photos.py
          site.py
          team.py

  composition/
    applications.py
```

Existing ACL and dispatch files are modified only at their dependency seams.

## 21. First implementation slice

Included:

- shared application/plugin value objects;
- Pydantic application/plugin descriptors;
- complete bundled 4.2.0 app metadata copy;
- complete bundled application-owned 4.2.0 plugin metadata copy;
- static catalog;
- ordered installation manifest;
- static registry;
- ACL write-side app validation;
- separation of handler registration from installation/plugin availability;
- dispatch app/plugin validation;
- composition wiring;
- characterization/unit/integration/architecture tests;
- architecture record update.

Excluded:

- runtime PHP/config parsing;
- filesystem discovery;
- application/plugin mutation;
- installer behavior;
- service-plugin families;
- event execution;
- application management HTTP/UI;
- dynamic installation-state caching.

## 22. Acceptance criteria

The slice is complete when:

1. no production application/plugin registry code executes or parses PHP;
2. bundled Webasyst 4.2.0 app/plugin metadata is represented through typed Python descriptors;
3. catalog inventory matches the exact supplied 4.2.0 source;
4. installation order and plugin ownership are explicit;
5. unknown/disabled application/plugin lookup is typed;
6. ACL writes reject unknown/disabled apps while ACL reads remain legacy-data compatible;
7. dispatch uses registry availability and handler registry only for handler lookup;
8. enabled-but-unimplemented dispatch is distinguishable from disabled installation state;
9. one registry instance is shared by ACL and dispatch through DI;
10. no new RBAC/database/runtime-PHP dependency is introduced;
11. architecture guards enforce the new boundaries;
12. the full existing test suite plus new registry tests passes.
