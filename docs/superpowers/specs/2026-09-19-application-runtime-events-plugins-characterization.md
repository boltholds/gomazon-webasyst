# Webasyst 4.2.0 Application Runtime, Events & Plugins — Characterization

Status: source-pinned
Date: 2026-09-19
Authoritative release commit: `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`
Commit message: `Webasyst Framework v.4.2.0`

This document records only behavior required by the first Python application-runtime/event/plugin slice.

| Case | 4.2.0 source | Observed behavior | Python consequence |
| --- | --- | --- | --- |
| Event identity | `waSystem::event()`, `waEvent::__construct()` | Event is identified by emitting app id + event name. | Use `EventKey(AppId, EventName)`. |
| App handler discovery | `waEvent::setHandlers()`, `parseAppsHandlersFiles()` | Scans handlers for `getApps(true)`, therefore includes the system `webasyst` app. | Python runtime registration may include system-app handlers but does not scan PHP at request time. |
| Handler filename | `parseAppsHandlersFiles()` | `<event-app>.<event>.handler.php` maps source app/event; handler app comes from directory owner; default method is `execute`. | Preserve subscription identity; never derive/import Python class from filename. |
| App wildcard declarations | `parseAppsWildCard()` | `wildcard.php` may override event source app, handler app, class and one/many methods. | Normalize only source/pattern/owner/method inventory; PHP class/file fields are non-executable metadata. |
| Plugin enablement | `waEvent::getPluginList()`, `waAppConfig::getPlugins()` | Reads `wa-config/apps/<app>/plugins.php`; only truthy entries are enabled. | Plugin catalog preserves PHP truth semantics. |
| Missing plugin list | same | Missing `plugins.php` means no plugins. | Empty plugin snapshot is normal. |
| Missing plugin manifest | same | Enabled plugin without `lib/config/plugin.php` is skipped. | Omit with diagnostics rather than fail whole startup. |
| Event plugin scan scope | `waEvent::setPlugins()` | Uses `wa()->getApps()`, which excludes system `webasyst`. | First legacy plugin discovery targets ordinary installed apps; system plugin mechanisms remain a later slice. |
| Simple plugin handlers | `parsePluginsHandlers()` | `handlers[event] = method|string-array` registers plugin handler for the plugin's own app as event source. | Normalize into declarative subscriptions. |
| Plugin wildcard handlers | `parsePluginWildCardHandlers()` | `handlers['*']` contains structured entries and may set cross-app `event_app_id`. | Event source selector is independent of handler/plugin owner. |
| Real cross-app example | `wa-apps/site/plugins/rublesign/lib/config/plugin.php` | Site plugin subscribes to `webasyst.backend_header`, `shop.frontend_head`, and `site.frontend_page`. | Cross-app subscriptions are required, not theoretical. |
| Implicit rights handler | `waEvent::getPluginList()`, `waAppConfig::getPlugins()` | Truthy `rights` injects `rights.config -> rightsConfig` if absent. | Normalize as compatibility declaration. |
| Implicit frontend handler | same | Truthy `frontend` injects `routing -> routing` if absent. | Normalize as compatibility declaration. |
| Implicit cron handler | `waEvent::getPluginList()` | Truthy `cron` injects `cron -> cron` if absent for event discovery. | Preserve declaration; scheduler execution remains out of scope. |
| Handler bucket order | `waEvent::run()` | exact app/exact name -> exact app/masked -> any app/exact -> any app/masked. | Registry matching must return this order. |
| App result ownership | `runApps()` | First non-null result is stored under handler app id; later handlers for that app are skipped once a result exists. | Explicit `ApplicationEventOwner` first-result state. |
| Plugin result ownership | `runPlugins()` | First non-null result per plugin; key is `plugin_id-plugin` for same-app events and `app_id_plugin_id-plugin` cross-app. | Explicit `PluginEventOwner` plus compatibility key projector. |
| Null/no result | `runApps()`, `runPlugins()` | Null result does not close owner; later matching method/handler may produce a result. | Model `EventHandlerNoResult` explicitly. |
| Handler exception | same | Exception is logged/debug-logged; dispatch continues. | Record diagnostics and continue; do not abort unrelated handlers. |
| Plugin `array_keys` | `runPlugins()` | Only plugin results are padded. Scalar becomes `['' => scalar]`; requested missing keys become empty strings. | Keep padding in Webasyst plugin-result projection, not event core. |
| App `array_keys` | `runApps()` | No equivalent padding is applied to ordinary app handler results. | Do not apply plugin padding globally. |
| Global before/after hooks | `waEvent::run()` | `eventHook`/ `eventHookAfter` can return arrays overriding dispatch result. | Reserve explicit interceptor boundary; do not recreate hidden SystemConfig hook now. |
| Pattern forms | `getRegex()` | Exact names, `prefix.*`, and raw regex beginning `/` or `~` are supported. | Exact/prefix are native typed variants; raw PCRE stays behind compatibility matcher. |
| Raw PCRE bundled usage survey | repository code search for bundled `plugin.php`/`wildcard.php` handler declarations | No bundled 4.2.0 raw-PCRE handler declaration was found in the surveyed source; framework capability still exists. | Raw PCRE is not required for first proof module; unsupported expressions must remain explicit rather than broadened silently. |

## Explicit boundaries

The first Python runtime slice does not execute:

- PHP application handlers;
- PHP plugin classes;
- plugin install/update scripts;
- SystemConfig event hooks;
- cron jobs;
- plugin settings/templates/assets;
- system `wa-plugins` lifecycle.

Legacy declarations are used as migration inventory. Executable behavior appears only after an explicit Python runtime module is linked.
