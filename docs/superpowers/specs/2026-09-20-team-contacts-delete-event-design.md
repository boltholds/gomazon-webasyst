# Team contacts.delete Nested Event Slice — Design

Status: implemented
Date: 2026-09-20

## Goal

Migrate the real Webasyst Team handler `contacts.delete.handler.php` and prove synchronous nested event publication through the Python runtime.

## EventPublisher boundary

Nested event emission uses the application-owned `EventPublisher` protocol:

```text
EventHandler
    |
    v
EventPublisher.publish(EventDispatchRequest)
    |
    v
EventDispatcher
```

Handlers do not depend on infrastructure registries, global event buses, composition globals, or request state.

`EventDispatcher` implements both:

- `dispatch()` for direct execution;
- `publish()` for the event-publisher port.

Both methods operate on the same linked registry.

## Runtime module factories

A bundled runtime module may need runtime services such as `EventPublisher` when constructing executable handlers. Prebuilding all modules before runtime registries exist creates an ordering cycle.

Production composition therefore uses explicit `KnownRuntimeModuleFactory` declarations:

```text
KnownRuntimeModuleFactory
    app_id
    build(EventPublisher) -> ApplicationRuntimeModule
```

Startup order:

1. create API/dispatch/event registries;
2. create `EventDispatcher`;
3. read canonical installed-application snapshot;
4. select known factories whose app ids are installed;
5. call selected factories with the publisher;
6. validate factory identity;
7. link resulting immutable runtime modules atomically.

No package scanning, dynamic imports, mutable late binding, or service locator is introduced.

Explicit test composition can still provide prebuilt modules through `ProvidedRuntimeModules`.

## Team relay

The Team factory registers one additional event definition:

```text
owner: team
source app: contacts
event: delete
handler: TeamContactsDeleteRelayHandler
```

The handler synchronously publishes:

```text
source app: team
event: contacts_delete
payload: exact same EventPayload object
```

and returns `EventHandlerNoResult`.

Nested dispatch reports are intentionally not projected into the outer event report because legacy Team ignores the return value of `wa('team')->event(...)`.

## Acceptance

Accepted when:

- Team relay unit test proves event key, same payload object and no-result outcome;
- nested runtime integration proves a Python handler subscribed to `team.contacts_delete` executes;
- nested handler result does not appear in outer `contacts.delete` report;
- Team factory is not invoked if Team is not installed;
- factory identity mismatch fails startup before linking;
- existing Team groups API remains green;
- full CI is green.
