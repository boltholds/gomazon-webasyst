# Static Application Registry Design

**Date:** 2026-09-19  
**Status:** accepted for implementation  
**Supersedes:** `docs/superpowers/specs/2026-09-15-application-registry-design.md` from archived branch `archive/application-registry-2026-09-15`  
**Scope:** framework-wide typed application/plugin catalog and read-only installation registry for the Python Webasyst 4.2.0 rewrite

## 1. Goal

Introduce one canonical typed source of truth for application and application-owned plugin availability.

The registry must answer four different questions without conflating them:

1. what applications/plugins are known to this Python implementation;
2. what applications/plugins are enabled in the current installation;
3. what normalized metadata belongs to each known application/plugin;
4. whether a consumer may resolve an application/plugin as enabled, disabled, owner-disabled, or unknown.

The first slice is read-only. Installation mutation, marketplace/update behavior, service plugins, event execution, and PHP config parsing are outside scope.

## 2. Why this slice is needed now

The current `main` already has three partially overlapping availability mechanisms:

- `InstalledAppDirectory` / `InMemoryInstalledAppDirectory` in API Execution;
- `OAuthConsentAppCatalog` / `InMemoryOAuthConsentAppCatalog` in OAuth authorization;
- plugin enablement state inside `DispatchRegistry` / `InMemoryDispatchRegistry`.

It also still defines `AppId` in `application/access_values.py`, although API Execution and OAuth already import it.

These are legitimate intermediate implementations, but they must not become permanent parallel sources of truth.

The Application Registry slice therefore replaces duplicated application/plugin availability state while preserving consumer-specific projections.

## 3. Authoritative legacy behavior

Webasyst Framework 4.2.0 source remains authoritative under ADR-015.

Relevant behavior:

- `waSystem::getApps()` reads enabled applications, loads each application descriptor, and appends the framework `webasyst` application;
- `waSystem::getApps(false)` omits `webasyst` from the ordinary application list;
- application order is observable and must be preserved;
- `waAppConfig::getPlugins()` combines enabled plugin state with plugin descriptor metadata;
- plugin ids are scoped to the owning application;
- legacy plugin metadata derives effective handlers from capability flags such as `rights` and `frontend`.

The supplied 4.2.0 source inventory represented by the static catalog contains these applications:

- `webasyst`
- `apiexplorer`
- `blog`
- `developer`
- `dummy`
- `installer`
- `photos`
- `site`
- `team`
- `ui`

Application-owned bundled plugins in scope:

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

Framework service-plugin families under `wa-plugins/*` are separate and are not part of this registry.

## 4. Non-goals

This slice does not implement:

- runtime PHP parsing or PHP execution;
- filesystem discovery of arbitrary applications;
- install/enable/disable/uninstall/update operations;
- writing Webasyst configuration files;
- Installer marketplace/update flows;
- payment/shipping/sms service-plugin registries;
- plugin event execution;
- plugin settings UI;
- rights-config rendering;
- application management HTTP APIs;
- registered OAuth clients;
- dynamic cache invalidation for future mutable installation state.

## 5. Architecture

The model is:

```text
StaticWebasyst42Catalog
          +
InstallationManifest
          |
          v
StaticApplicationRegistry
          |
          +--> ACL mutation validation
          +--> Dispatch availability
          +--> API Execution installed-app resolution
          +--> OAuth consent projection
```

Catalog knowledge and installation enablement are separate concepts.

### 5.1 Static catalog

The static catalog is immutable normalized metadata copied from the exact Webasyst 4.2.0 source.

It answers what the rewrite knows, not what is currently enabled.

### 5.2 Installation manifest

The manifest is immutable ordered installation state for one composed runtime.

It contains application/plugin identities only and never duplicates descriptor metadata.

### 5.3 Application registry

`StaticApplicationRegistry` combines the catalog and manifest.

It is application-layer code and must not import the concrete Webasyst catalog. Composition supplies the concrete catalog and manifest.

Only one registry instance is composed for the runtime and shared across consumers.

## 6. Shared value objects

`AppId` is framework-wide and moves to:

`src/gomazon_webasyst/application/app_values.py`

The same module owns:

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

`access_values.py` may temporarily re-export `AppId` during migration, but there must be exactly one concrete `AppId` class.

No consumer-specific duplicate AppId type is allowed.

## 7. Domain taxonomy

The slice follows the Entity / VO / Service / Composite taxonomy already used by newer subsystems.

### Entities

- `ApplicationDescriptor` identified by `AppId`;
- `PluginDescriptor` identified by `PluginRef`.

### Value Objects

- `AppId`;
- `PluginId`;
- `PluginRef`;
- `InstalledApplication`;
- `InstallationManifest`;
- normalized routing/header/plugin integration values.

### Services

- `StaticApplicationRegistry`;
- consumer-specific projection services such as the OAuth consent adapter.

No new orchestration Composite is required in the first slice because the registry performs deterministic read-only resolution over immutable values.

## 8. Typed descriptors

Cross-boundary application/plugin descriptors use Pydantic v2 and `extra="forbid"`.

Canonical descriptors must not contain `dict[str, Any]`, opaque metadata bags, nullable control bags, or raw PHP values.

### 8.1 ApplicationDescriptor

At minimum it contains:

- `id: AppId`;
- name;
- version;
- vendor;
- description;
- icon/presentation data where present;
- normalized UI-version support;
- explicit capability flags;
- ordered routing parameters;
- header items;
- normalized framework metadata needed by consumers.

Absent boolean capabilities normalize to `False`.

### 8.2 PluginDescriptor

At minimum it contains:

- `ref: PluginRef`;
- name;
- version;
- vendor;
- description;
- icon/presentation data where present;
- explicit capability flags;
- normalized integration state;
- normalized event-handler declarations.

Correlated states such as external-calendar integration use structural variants rather than booleans plus nullable companion fields.

## 9. Catalog layout

Webasyst-specific data lives under compatibility:

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

`catalog.py` assembles immutable typed descriptor tuples and validates duplicate ids/refs.

No runtime PHP parser is introduced.

## 10. Installation manifest

Use an ordered structural manifest:

```python
@dataclass(slots=True, frozen=True)
class InstalledApplication:
    app_id: AppId
    plugins: tuple[PluginId, ...]

@dataclass(slots=True, frozen=True)
class InstallationManifest:
    apps: tuple[InstalledApplication, ...]
```

Registry construction rejects:

- duplicate installed application ids;
- duplicate plugins within one application;
- unknown installed applications;
- unknown installed plugins;
- plugin ownership mismatch;
- missing required system application `webasyst`.

These are startup/configuration failures, not ordinary lookup results.

The default bundled compatibility profile, when used, is ordered:

1. `team`
2. `site`
3. `blog`
4. `photos`
5. `webasyst`

No application-owned plugins are implicitly enabled by that default profile.

## 11. Resolution model

Expected misses and disabled states are explicit typed results.

Application resolution:

```text
ApplicationResolution
├── ApplicationEnabled(descriptor)
├── ApplicationDisabled(descriptor)
└── ApplicationUnknown(app_id)
```

Plugin resolution:

```text
PluginResolution
├── PluginEnabled(descriptor)
├── PluginDisabled(descriptor)
├── PluginOwnerDisabled(descriptor, owner)
└── PluginUnknown(plugin_ref)
```

Canonical APIs never encode these outcomes as `None`, bool, empty string, or exceptions.

## 12. ApplicationRegistry port

Application-owned port:

```python
class ApplicationRegistry(Protocol):
    def resolve_app(self, app_id: AppId) -> ApplicationResolution: ...
    def resolve_plugin(self, plugin_ref: PluginRef) -> PluginResolution: ...
    def list_catalog_apps(self) -> tuple[ApplicationDescriptor, ...]: ...
    def list_enabled_apps(self) -> tuple[ApplicationDescriptor, ...]: ...
    def list_enabled_apps_including_system(self) -> tuple[ApplicationDescriptor, ...]: ...
    def list_plugins(self, app_id: AppId) -> PluginListResult: ...
    def list_enabled_plugins(self, app_id: AppId) -> PluginListResult: ...
```

The first implementation is synchronous because it resolves immutable in-memory values and performs no I/O.

Future mutable/persistent installation state may introduce a different adapter boundary, but consumers must not be redesigned around a database today.

## 13. API Execution integration

The current `InstalledAppDirectory` is an intermediate parallel availability source.

After this slice, API Execution uses `ApplicationRegistry` as the source of installed-app truth.

Preferred migration:

- `ApiRequestAuthorizer` receives `ApplicationRegistry`;
- app authorization requires `ApplicationEnabled`;
- `ApplicationDisabled` and `ApplicationUnknown` map to the existing API-level app-not-found/unavailable rejection required by compatibility;
- `InMemoryInstalledAppDirectory` is removed from production composition.

A temporary adapter implementing the old `InstalledAppDirectory` port may exist only during the same migration branch and must delegate to `ApplicationRegistry`; it may not own another set of ids.

The end state has no parallel installed-app set.

## 14. OAuth authorization integration

`OAuthConsentAppCatalog` remains a consumer-specific projection boundary, not a second application source of truth.

Replace production `InMemoryOAuthConsentAppCatalog` with a registry-backed adapter/service:

```text
ApplicationRegistry
        |
        v
RegistryBackedOAuthConsentAppCatalog
        |
        v
OAuthConsentScopeService
```

The adapter converts an enabled application descriptor into `OAuthConsentApplication` display metadata.

Unknown/disabled applications are not exposed as consent applications.

OAuth continues to own consent-specific Entity/VO types; the generic registry does not import OAuth.

## 15. Dispatch integration

Current `DispatchRegistry` mixes handler registration with plugin availability.

Split it into:

- `HandlerRegistry`: Python handler registration/lookup only;
- `ApplicationRegistry`: application/plugin installation availability.

`InMemoryDispatchRegistry.enable_plugin()` and its plugin set are removed.

`DispatchResolver` receives both ports.

App namespace resolution:

```text
resolve app availability
  -> require ApplicationEnabled
  -> resolve registered Python handler
```

Plugin namespace resolution:

```text
resolve PluginRef
  -> require PluginEnabled
  -> resolve registered Python handler
```

Enabled but unimplemented targets remain dispatch-target-not-found rather than being mislabeled as disabled.

## 16. Access-control integration

ACL reads/evaluation remain registry-independent so legacy persisted rights for unknown or disabled apps remain observable.

Only new app-scoped mutations validate the registry:

- `AssignRight`;
- `RevokeRight`;
- `SetAppAccess`.

Before mutation planning/writes they require `ApplicationEnabled`.

Add explicit rejection reasons:

- `APPLICATION_NOT_FOUND`;
- `APPLICATION_DISABLED`.

The registry does not enter `RightsEvaluator`.

## 17. Composition

Composition constructs exactly one `StaticApplicationRegistry` from the Webasyst catalog and installation manifest.

That same instance is injected into:

- API Execution;
- OAuth consent projection;
- dispatch;
- ACL mutation use cases.

No consumer may construct its own independent set of enabled applications/plugins.

The application container may expose the registry for sub-composition, but it must not become a global service locator.

## 18. Dependency direction

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
 infrastructure / static compatibility data
```

Application registry code must not import SQLAlchemy, FastAPI, Starlette, OAuth compatibility code, ACL compatibility code, or concrete Webasyst descriptor modules.

## 19. Testing

### Unit

Cover:

- AppId/PluginId/PluginRef validation;
- catalog duplicate detection;
- manifest invariants;
- ordering;
- application resolution;
- plugin resolution;
- list results;
- descriptor serialization.

### Compatibility characterization

Pin:

- exact bundled application inventory;
- exact bundled application-owned plugin inventory;
- default app ordering;
- system-app listing semantics;
- representative descriptor metadata;
- derived plugin handlers.

### Integration

Cover one registry instance driving:

- API app resolution;
- OAuth consent app projection;
- dispatch app/plugin availability;
- ACL mutation validation.

### Architecture

Enforce:

- one concrete `AppId`;
- no application-registry import of compatibility/infrastructure/presentation;
- no handler registry installation state;
- no production `InMemoryInstalledAppDirectory` after migration;
- no production standalone in-memory OAuth app catalog;
- no `Optional`/bool sentinel lookup state;
- no opaque descriptor metadata bags.

## 20. Migration order

The implementation order is intentionally incremental:

1. move shared AppId and add PluginId/PluginRef;
2. add typed descriptor/result contracts;
3. implement static registry core and tests;
4. add Webasyst 4.2.0 static catalog and characterization;
5. migrate API Execution;
6. migrate dispatch;
7. migrate ACL mutations;
8. migrate OAuth consent projection;
9. centralize composition;
10. delete transitional duplicate availability stores;
11. add architecture guards and update AGENTS.md.

Each step must keep CI green.

## 21. Explicitly deferred work

Later slices may add:

- mutable installation state;
- installer/update workflows;
- service-plugin registries;
- event execution;
- plugin lifecycle hooks;
- registered OAuth clients;
- runtime descriptor discovery for non-bundled Python-native applications.

Those extensions must build on the same shared identities and must not reintroduce parallel application truth.
