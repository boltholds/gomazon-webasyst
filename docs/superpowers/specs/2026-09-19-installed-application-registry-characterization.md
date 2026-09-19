# Webasyst 4.2.0 Installed Application Discovery — Source Characterization

Status: accepted characterization
Date: 2026-09-19

## Authoritative snapshot

The exact public release commit used for this characterization is:

- repository: `webasyst/webasyst-framework`
- commit: `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`
- commit title: `Webasyst Framework v.4.2.0`
- release commit date: 2026-07-27

This commit is used as the source-backed cross-check for the supplied 4.2.0 archive. Later upstream `master` behavior is not authoritative for this slice.

## Evidence table

| Case | 4.2.0 source location | Exact observed behavior | Implementation consequence |
| --- | --- | --- | --- |
| Missing `wa-config/apps.php` | `wa-system/waSystem.class.php::getApps()` | Sets the static app cache to an empty array and throws `waException('File wa-config/apps.php not found.', 600)`. | Python discovery treats a missing apps config as startup/configuration failure, not an ordinary app lookup miss. |
| Configured app list | `waSystem::getApps()` | Includes `wa-config/apps.php` as an ordered PHP array and then assigns `$all_apps['webasyst'] = true`. | Configured order is preserved; `webasyst` is forced into the runtime set even if absent from apps.php. |
| Enabled/disabled entry | `waSystem::getApps()` | Iterates `foreach ($all_apps as $app => $enabled)` and enters discovery only when `if ($enabled)` is truthy. | Normalizer must use PHP truth semantics for the supported scalar subset; false, 0, 0.0, empty string, string `"0"`, null and empty array are disabled. |
| Installer WAID auto-enable | `waSystem::getApps()` | If `empty($all_apps['installer'])`, reads `webasyst/waid_credentials`; `installer` becomes `!!$waid_enabled`. Any thrown `Throwable` is ignored. | Legacy discovery policy must reproduce this only when a settings source is available; otherwise the adapter must expose an explicit policy seam rather than hard-code database access into the parser. |
| App manifest missing | `waSystem::getApps()` | For an enabled app, resolves `lib/config/app.php`; if the file does not exist, it executes `continue`. | A configured app with no manifest is omitted from the snapshot rather than turning into a broken Entity. Diagnostics may be recorded, but lookup later returns missing. |
| Framework app path | `waSystem::getAppPath()` + `getApps()` | `webasyst` resolves under `wa_path_system/webasyst`, so its manifest is `wa-system/webasyst/lib/config/app.php`; ordinary apps use `wa-apps/<id>`. | Path policy has an explicit system-app branch and no request-controlled path construction. |
| Framework manifest | `wa-system/webasyst/lib/config/app.php` at release commit | Name `Webasyst`, vendor `webasyst`, version/critical `4.2.0`, CSRF enabled, settings header item icon `img/wa-settings/settings.svg`. | Canonical catalog includes a `webasyst` Entity sourced from the system manifest. |
| `build.php` | `waSystem::getApps()` | If present, its included value becomes `app_info['build']`; otherwise build is `time()` in debug and `0` outside debug. | Build is cache/runtime metadata and is not required by current API/OAuth consumers. It is deliberately omitted from the first canonical Entity and may be added later as a consumer-driven VO. |
| App id metadata | `waSystem::getApps()` | Assigns `$app_info['id'] = $app` and later stores `array('id' => $app) + $app_info`. | `AppId` is catalog identity; a manifest cannot override it. |
| Localization | `waSystem::getApps()` | Loads the app locale domain and replaces `app_info['name']` with `_wd($app, ...)`; header-item names are also translated. Cache file is locale-specific (`config/apps<locale>`). | A single shared Python startup catalog must remain locale-neutral. It stores the raw manifest default name; locale-specific display projection is a later boundary. OAuth initially displays the manifest default name and must not claim localized UI parity until that projection exists. |
| Scalar `icon` | `waSystem::getApps()` | Scalar icon becomes a size-48 icon whose path is prefixed with the app path relative to framework root. | Normalize scalar icon into `ApplicationIcon(size=48, ...)`. |
| Icon-size map | `waSystem::getApps()` | If `icon` is an array, every size/value entry is path-prefixed. No bundled app in the 4.2.0 release commit needs this shape, but the loader explicitly supports it. | Keep a synthetic source-contract fixture and support the branch in the normalizer. |
| `img` fallback | `waSystem::getApps()`; bundled Developer app manifest | Explicit `img` is path-prefixed. If no `img` but icon 48 exists, `img` becomes icon 48. If `img` exists, missing icon sizes 48, 24 and 16 are filled from it/each other. | Normalizer must reproduce this asset fallback before building immutable icon metadata. |
| Header item assets | `waSystem::getApps()` | Header item names are localized. Asset prefix is ordinary app path, except `webasyst` uses literal `wa-content/`. Scalar header icon becomes size 48; `img` falls back from icon 48. | Header items are normalized separately; the `webasyst` settings icon becomes `wa-content/img/wa-settings/settings.svg`. |
| `getApps(false)` | `waSystem::getApps()` | Returns loaded apps with `webasyst` removed; `getApps(true)` returns the system-inclusive set. | Canonical internal catalog is system-inclusive because API/OAuth need `webasyst`; consumer listings may project it out. |
| `appExists('webasyst')` | `waSystem::appExists()` | Calls `getApps()`, then returns true for literal `webasyst` or any loaded app key. | The canonical catalog must contain the characterized system Entity; application services should not scatter literal special cases. |
| `getAppInfo()` | `waSystem::getAppInfo()` | Calls `appExists()` and returns the corresponding loaded app info; ordinary missing app yields null in legacy code. | Python converts ordinary miss to explicit `InstalledApplicationMissing`; `None` does not cross the application port. |
| Malformed/non-array config | `waSystem::getApps()` | Legacy code performs array offset writes/indexing immediately after `include`; there is no validation/skip path for structurally invalid returned values. Modern PHP therefore fails rather than treating malformed config as an absent app. | Python discovery fails startup/configuration deterministically for malformed supported config instead of silently omitting it. |
| Dynamic PHP in config | PHP `include` behavior in legacy loader | Legacy execution can evaluate arbitrary PHP in config files. | Python intentionally does not preserve code execution. Unsupported dynamic expressions fail closed in the restricted parser. This is a security boundary, not a parser bug. |

## Fixture provenance

The fixture directory is `tests/fixtures/webasyst_4_2/application_registry/`.

`source-reduced` fixtures contain only the minimal declarative fragment needed from files at release commit `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`:

- `app_scalar_icon.php` — reduced from `wa-apps/site/lib/config/app.php`;
- `app_img_fallback.php` — reduced from `wa-apps/developer/lib/config/app.php`;
- `app_header_items.php` and `webasyst_app.php` — reduced from `wa-system/webasyst/lib/config/app.php`.

`synthetic-*` fixtures are deliberately labeled and are not claimed as verbatim repository files:

- `apps_enabled_disabled.php` models the runtime `wa-config/apps.php` shape consumed by `getApps()`; that installation-specific file is not a repository release artifact;
- `app_icon_map.php` exercises the explicit icon-array loader branch even though bundled 4.2.0 manifests use scalar icons/img;
- `unsupported_dynamic.php` is a security case proving the future parser fails closed rather than emulating legacy PHP execution.

## Decisions fixed by characterization

1. Missing `apps.php` is a configuration failure.
2. Enabled app + missing manifest is skipped/omitted.
3. `webasyst` is forced into discovery and sourced from `wa-system/webasyst/lib/config/app.php`.
4. Installer WAID auto-enable is real 4.2.0 behavior and must live behind a compatibility policy/settings seam.
5. Build metadata is excluded from the first canonical Entity because current consumers do not use it.
6. Canonical names are locale-neutral raw manifest names. Legacy localization becomes a later consumer projection; this slice does not claim localized OAuth consent parity.
7. Asset normalization reproduces scalar/map icon and img fallback behavior.
8. Webasyst header-item asset prefix is `wa-content/`, yielding the OAuth settings icon path `wa-content/img/wa-settings/settings.svg`.
9. Dynamic PHP execution is intentionally not supported; the parser rejects it.

These decisions are authoritative for the implementation plan unless a future characterization against the supplied 4.2.0 archive demonstrates a mismatch with release commit `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`.
