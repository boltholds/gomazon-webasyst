# Team contacts.contacts_collection relay — Design

Status: implemented
Date: 2026-09-22
Authoritative source: Webasyst Framework 4.2.0 release commit `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`

## Goal

Migrate the Team handler for the external `contacts.contacts_collection` event through the existing installed-application event runtime.

The legacy handler is intentionally small but semantically different from the already-migrated `contacts.delete` relay: it returns a boolean derived from the nested Team event result.

## Source behavior

Legacy source:

```php
return !!wa('team')->event('contacts_collection', $params);
```

The same payload is passed by reference to `team.contacts_collection`.

`waEvent::run()` returns an array containing owner results for handlers that returned anything other than PHP `null`.

Therefore the outer boolean depends on whether that result array is empty:

- empty nested result array -> false;
- any nested non-null owner result -> true;
- nested handler returning false -> still true at the outer relay because false is non-null and occupies a result-array entry;
- nested failures without a returned result -> false.

## Python mapping

The outer handler is `TeamContactsCollectionRelayHandler`.

It publishes:

```text
EventKey(team, contacts_collection)
```

with the exact same `EventPayload` object received from the outer event.

The nested `EventDispatchReport` is projected as:

```text
bool(report.results)
```

and returned as:

```text
EventHandlerReturned(
    LegacyEventPayload(value=<boolean>)
)
```

The false case MUST NOT become `EventHandlerNoResult`.

## Runtime registration

The installed Team runtime registers the relay as:

```text
owner: team
source: contacts
event: contacts_collection
handler: team-contacts-collection-relay
```

It is registered alongside the existing `contacts.delete` Team relay.

## Non-goals

This slice does not migrate the consumers of `team.contacts_collection` themselves. Application/plugin handlers may be migrated independently through the same event registry.

It also does not add Contacts UI rendering or a new HTTP endpoint.

## Acceptance

Complete when:

- source behavior is release-pinned;
- payload identity is preserved across nested publication;
- empty nested results produce returned boolean false;
- a nested returned false payload produces returned boolean true;
- nested failure without a result produces returned boolean false;
- Team runtime registration is explicit;
- full CI is green.
