# Webasyst 4.2.0 Team contacts.contacts_collection relay — Characterization

Status: source-pinned
Date: 2026-09-22
Authoritative release commit: `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`

## Source

Outer handler:

`wa-apps/team/lib/handlers/contacts.contacts_collection.handler.php`

Runtime result semantics:

`wa-system/event/waEvent.class.php::run()`

## Observed behavior

The Team handler for the external `contacts.contacts_collection` event contains one operation:

```php
return !!wa('team')->event('contacts_collection', $params);
```

The same payload object is passed by reference to the nested Team event.

Unlike `contacts.delete`, this relay does return a value to the outer event. The return value is always boolean.

`waSystem::event()` returns the array produced by `waEvent::run()`. That array contains one entry per application/plugin owner whose selected handler returned a value other than PHP `null`. Therefore:

- no nested non-null results -> empty array -> outer `false`;
- at least one nested non-null result -> non-empty array -> outer `true`;
- a nested handler returning PHP `false` still creates an array entry and therefore makes the outer relay return `true`;
- nested handler exceptions that produce no result do not make the result array non-empty.

The boolean is about result presence, not result truthiness.

## Python consequence

The migrated outer handler republishes the exact same `EventPayload` as:

```text
team.contacts_collection
```

It then maps `bool(EventDispatchReport.results)` into:

```text
EventHandlerReturned(
    LegacyEventPayload(value=<boolean>)
)
```

It must never use `EventHandlerNoResult`, even when the boolean is false, because PHP `false !== null` and is therefore an observable owner result in the outer event.

The existing event runtime already models non-null result presence through `EventHandlerReturned`, including returned false-like payload values.
