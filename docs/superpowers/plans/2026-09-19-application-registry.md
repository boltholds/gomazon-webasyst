# Application Registry Implementation Plan

**Date:** 2026-09-19  
**Branch:** `feature/application-registry`  
**Design:** `docs/superpowers/specs/2026-09-19-application-registry-design.md`

## Goal

Implement one framework-wide typed `ApplicationRegistry` and migrate API Execution, dispatch, ACL mutation validation, and OAuth consent to that single application/plugin availability source.

The plan is intentionally incremental. Every task should leave the branch testable and avoid a second long-lived source of installed-app/plugin truth.

## Baseline

Current `main` at plan creation:

- head: `1012b7d51a796e29751f71d24b5e2a5160905e0e`
- CI run 361: success
- OAuth authorization surface merged
- current duplicate availability mechanisms:
  - `InstalledAppDirectory`
  - `OAuthConsentAppCatalog`
  - plugin state in `DispatchRegistry`

Old application-registry work is preserved at:

`archive/application-registry-2026-09-15`

## Task 1 — Move AppId to framework-wide app values

### Production

Create:

- `src/gomazon_webasyst/application/app_values.py`

Move the concrete `AppId` definition there and add:

- `PluginId`
- `PluginRef`

Keep a temporary re-export from `application/access_values.py` so existing ACL imports do not break in the same commit.

Update direct imports in newer subsystems to prefer `application.app_values.AppId`.

### Tests

Add:

- `tests/unit/test_app_values.py`

Cover:

- non-empty AppId;
- existing length limit;
- non-empty PluginId;
- PluginRef value semantics;
- `access_values.AppId is app_values.AppId`.

### Architecture guard

Add/extend architecture test so there is exactly one concrete `class AppId` under `src/gomazon_webasyst/application`.

### Commit

`refactor: promote application identifiers to shared values`

---

## Task 2 — Add typed application-registry contracts

### Production

Create:

- `src/gomazon_webasyst/contracts/applications.py`
- registry-related enums in `contracts/enums.py`
- `src/gomazon_webasyst/application/ports/application_registry.py`

Define Pydantic descriptor models for:

- application presentation;
- application capabilities;
- routing parameters;
- header items;
- plugin capabilities;
- plugin integration variants;
- plugin event handlers;
- `ApplicationDescriptor`;
- `PluginDescriptor`.

Define explicit lookup variants:

- `ApplicationEnabled`
- `ApplicationDisabled`
- `ApplicationUnknown`
- `PluginEnabled`
- `PluginDisabled`
- `PluginOwnerDisabled`
- `PluginUnknown`

Define explicit plugin-list results for known/enabled/disabled/unknown owner states.

No `Optional`, bool availability result, or metadata `dict[str, Any]`.

### Tests

Add:

- `tests/unit/test_application_registry_contracts.py`
- `tests/architecture/test_application_registry_boundaries.py`

Cover discriminators, serialization, forbidden extras, and dependency boundaries.

### Commit

`feat: add application registry contracts`

---

## Task 3 — Implement InstallationManifest and StaticApplicationRegistry

### Production

Create:

- `src/gomazon_webasyst/application/application_registry.py`

Add immutable VOs:

- `InstalledApplication`
- `InstallationManifest`
- `ApplicationCatalog`

Implement `StaticApplicationRegistry`.

Validate at construction:

- duplicate catalog app ids;
- duplicate catalog plugin refs;
- duplicate installed app ids;
- duplicate plugin ids within one app;
- unknown installed apps;
- unknown installed plugins;
- plugin ownership mismatch;
- required `webasyst` system app.

Implement:

- `resolve_app`
- `resolve_plugin`
- `list_catalog_apps`
- `list_enabled_apps`
- `list_enabled_apps_including_system`
- `list_plugins`
- `list_enabled_plugins`

### Tests

Add:

- `tests/unit/test_application_registry.py`

Use a small synthetic typed catalog, not Webasyst constants.

Test every result branch and ordering invariant.

### Commit

`feat: implement static application registry`

---

## Task 4 — Add Webasyst 4.2.0 static catalog inventory

### Production

Create:

- `src/gomazon_webasyst/compatibility/webasyst/applications/__init__.py`
- `catalog.py`
- descriptor modules for the ten bundled applications;
- plugin descriptor modules for Blog, Photos, Site, Team.

The first catalog commit may start with identity/name/version/capability fields required by current consumers, but every represented field must be sourced and characterized. Do not add guessed values.

Add:

- `WEBASYST_42_CATALOG`
- `DEFAULT_WEBASYST_42_INSTALLATION_MANIFEST`

Default manifest order:

`team, site, blog, photos, webasyst`

No plugins enabled by default.

### Tests

Add:

- `tests/compatibility/test_webasyst_application_catalog_characterization.py`

Pin exact inventory:

- 10 applications;
- 21 application-owned plugins;
- representative owner mappings;
- default order;
- `webasyst` system semantics;
- representative derived plugin handlers.

### Commit

`feat: add webasyst 4.2 application catalog`

---

## Task 5 — Migrate API Execution from InstalledAppDirectory

### Production

Update:

- `application/api_execution/services/authorizer.py`
- `composition/api_execution.py`
- related tests/fakes.

`ApiRequestAuthorizer` receives `ApplicationRegistry`.

Authorization order remains:

1. installed/available app;
2. app access;
3. scope;
4. license.

Map:

- `ApplicationEnabled` -> continue;
- `ApplicationDisabled` -> existing compatibility app-unavailable/not-found rejection;
- `ApplicationUnknown` -> existing compatibility app-unavailable/not-found rejection.

Delete production ownership of installed app ids from:

- `application/ports/installed_apps.py`
- `infrastructure/api_execution/app_directory.py`

A short-lived adapter is allowed only if required to keep an intermediate commit compiling; it must delegate to ApplicationRegistry and be removed before the task closes.

### Tests

Update:

- `tests/unit/test_api_request_authorizer.py`
- `tests/unit/test_api_execution_container.py`
- integration API tests.

Add an architecture assertion that API Execution no longer composes `InMemoryInstalledAppDirectory`.

### Commit

`refactor: source api app availability from application registry`

---

## Task 6 — Split dispatch handler registration from installation state

### Production

Replace application-owned `DispatchRegistry` port with handler-only `HandlerRegistry`.

Update:

- `application/ports/dispatch_registry.py` or rename to `handler_registry.py`;
- `compatibility/webasyst/dispatch/registry.py`;
- `compatibility/webasyst/dispatch/resolver.py`;
- composition and tests.

Remove:

- `enable_plugin()`;
- `plugin_available()`;
- plugin set from `InMemoryDispatchRegistry`;
- `PluginAvailable` / `PluginMissing` registry lookup contracts if no longer used.

`DispatchResolver` receives:

- `HandlerRegistry`
- `ApplicationRegistry`

App namespace requires `ApplicationEnabled`.

Plugin namespace resolves `PluginRef` and requires `PluginEnabled`.

Enabled but missing handler must still produce `DispatchTargetNotFound`.

### Tests

Update/add:

- `tests/unit/test_dispatch_registry.py`
- `tests/unit/test_dispatch_resolver.py`
- architecture guard that handler registry has no installation state.

Cover unknown, disabled, owner-disabled, enabled-with-handler, and enabled-without-handler.

### Commit

`refactor: separate dispatch handlers from app availability`

---

## Task 7 — Validate ACL app-scoped mutations through ApplicationRegistry

### Production

Inject `ApplicationRegistry` into app-scoped ACL mutation use cases:

- `AssignRight`
- `RevokeRight`
- `SetAppAccess`

Do not add the registry to ACL read/evaluation paths.

Add `AccessMutationRejectReason` values:

- `APPLICATION_NOT_FOUND`
- `APPLICATION_DISABLED`

Required sequence stays inside the mutation UoW:

1. authorize actor;
2. validate target;
3. resolve app availability;
4. build compatibility mutation plan;
5. execute writes;
6. commit.

### Tests

Update:

- ACL mutation unit tests;
- access-control composition tests;
- SQLite vertical integration tests.

Explicitly prove existing rights for disabled/unknown apps remain readable.

### Commit

`feat: validate acl mutations against application registry`

---

## Task 8 — Back OAuth consent catalog with ApplicationRegistry

### Production

Keep `OAuthConsentAppCatalog` as the OAuth-specific projection port.

Replace `InMemoryOAuthConsentAppCatalog` production usage with a registry-backed implementation/service.

Suggested location:

- `application/oauth_authorization/services/app_catalog.py`

It depends on `ApplicationRegistry` and converts an enabled `ApplicationDescriptor` to `OAuthConsentApplication`.

The generic registry must not import OAuth types.

Unknown or disabled applications map to OAuth catalog missing.

Remove empty standalone production OAuth catalog composition.

### Tests

Update:

- `tests/unit/test_oauth_consent_catalog.py`
- `tests/unit/test_oauth_authorization_container.py`
- OAuth integration flow.

Prove consent display metadata comes from the same enabled app descriptor used elsewhere.

### Commit

`refactor: project oauth consent apps from application registry`

---

## Task 9 — Compose one shared registry instance

### Production

Create:

- `src/gomazon_webasyst/composition/applications.py`

Build one registry from:

- `WEBASYST_42_CATALOG`
- configured/injected `InstallationManifest`.

Expose it through the root container.

Inject that exact instance into:

- API Execution;
- OAuth authorization;
- dispatch;
- ACL mutation use cases.

Do not recreate registry instances per request or subcomponent.

### Tests

Add:

- `tests/unit/test_application_registry_container.py`
- root container identity assertions.

### Commit

`feat: compose shared application registry`

---

## Task 10 — Remove transitional duplicate availability stores

Delete or retire:

- `InstalledAppDirectory` if no longer referenced;
- `InMemoryInstalledAppDirectory`;
- standalone production `InMemoryOAuthConsentAppCatalog`;
- plugin availability state in dispatch;
- obsolete enums/contracts used only by those implementations.

Use repository-wide search plus architecture tests to prove no duplicate availability set remains.

### Tests

Full unit + integration + architecture suite.

### Commit

`refactor: remove duplicate application availability stores`

---

## Task 11 — Update architecture record and ADRs

Update `AGENTS.md`:

- add application-registry design/plan companion artifacts;
- add new ADRs with non-conflicting numbers after ADR-044;
- update target package layout;
- update API Execution, dispatch, OAuth, ACL, and application-registry compatibility rules;
- add agent rules preventing parallel installed-app/plugin state;
- add application-registry completion criteria.

Proposed ADRs:

- ADR-045 — bundled application/plugin metadata is a static typed catalog;
- ADR-046 — ApplicationRegistry is the sole installation-availability source;
- ADR-047 — consumer-specific app catalogs are projections over ApplicationRegistry.

### Commit

`docs: record application registry architecture`

---

## Task 12 — Final verification

Run the full CI suite on the branch.

Required final assertions:

- one concrete AppId class;
- one composed ApplicationRegistry instance;
- API Execution has no independent installed-app set;
- dispatch handler registry has no plugin availability state;
- OAuth consent app catalog owns no independent application set;
- ACL reads remain registry-independent;
- ACL app-scoped writes reject unknown/disabled apps;
- Webasyst catalog inventory is characterized;
- architecture Optional/None guards remain green.

Only after the branch CI is green and `main...feature/application-registry` is reviewed should it be merged.
