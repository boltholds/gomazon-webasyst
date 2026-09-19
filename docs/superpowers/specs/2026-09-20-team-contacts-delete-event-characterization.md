# Webasyst 4.2.0 Team contacts.delete Event Relay — Characterization

Status: source-pinned
Date: 2026-09-20
Authoritative release commit: `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`

## Source locations

- `wa-apps/team/lib/handlers/contacts.delete.handler.php`
- `wa-system/waSystem.class.php::event()`
- `wa-system/event/waEvent.class.php::run()`

## Exact behavior

| Case | Webasyst 4.2.0 behavior | Python consequence |
| --- | --- | --- |
| Subscription source | Handler filename is `contacts.delete.handler.php`. Legacy handler discovery maps it to source app `contacts`, event `delete`, handler app `team`. | Team runtime registers an explicit handler owned by Team for exact source `contacts.delete`. |
| Handler body | `execute(&$params)` calls `wa('team')->event('contacts_delete', $params)`. | Relay publishes a new event instead of executing PHP or deriving a class name. |
| Nested source app | `wa('team')` returns the Team system instance; calling `event('contacts_delete', ...)` with a string name derives `event_app_id` from that instance's application config. | Nested event key is exactly `EventKey(AppId("team"), EventName("contacts_delete"))`. |
| Payload identity | Both handler parameter and `waSystem::event()` parameter are passed by reference. | Relay passes the same `EventPayload` object to the nested publication; it does not serialize/copy/project between the two dispatches. |
| Nested result | `waSystem::event()` returns the nested `waEvent::run()` result, but Team handler does not `return` that call. PHP method therefore returns `null`. | Relay ignores nested dispatch results and returns `EventHandlerNoResult`. |
| Outer first-result semantics | Because Team handler returns null, it does not close Team as a result owner for the outer `contacts.delete` event. | Outer dispatch receives no Team result from this relay. |
| Nested handler failures | `waEvent::runApps/runPlugins` catch ordinary handler exceptions and continue. | Nested dispatcher records ordinary handler failures in its own report; relay still returns no result unless publication itself raises. |
| Global active-app state | Legacy event machinery temporarily changes/restores active app internally. | Python does not recreate active-app globals; source app is explicit in `EventKey`. |

## Non-goals

This slice does not migrate consumers of `team.contacts_delete` from third-party plugins/apps, contact deletion HTTP flows, Team contact cleanup, or general PHP event-file discovery.

The proof is event-runtime behavior: an outer `contacts.delete` dispatch reaches the Team relay, which synchronously publishes `team.contacts_delete` to already-linked Python handlers with the same payload object and leaves the outer result empty.
