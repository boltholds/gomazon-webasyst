# Contacts Private Rights Delete Event — Design

Status: implemented
Date: 2026-09-20

## Goal

Close the app-private cleanup that was deliberately deferred from the contact-core delete slice. A real `contacts.delete` publication now reaches an installed Contacts runtime handler and removes that application's `contacts_rights` rows without teaching the core contact repository about Contacts-app storage.

## Source boundary

The old Contacts application is separately versioned from the framework source used by the Webasyst 4.2.0 framework characterizations. The exact handler/schema behavior for this slice is pinned to Contacts 1.1.7 source commit `dc497e33fb7d33d40c8a897051fa8ed3d2657441`.

The source handler:

1. receives `contacts.delete` params by reference;
2. casts params to an array;
3. maps each contact id to its negative integer form;
4. deletes `contacts_rights` rows by `group_id`;
5. returns no event result.

The app-private table has composite primary key `(group_id, category_id)` and a `writable` flag. It is distinct from framework `wa_contact_rights`.

## Application boundary

The application-owned contract is:

```text
DeleteContactsPrivateRights
    -> ContactsPrivateRightsCleaner
    -> ContactsPrivateRightsDeleted
```

The input remains the existing immutable `ContactDeletionBatch` with positive contact ids. The negative legacy principal encoding does not appear in application or compatibility contracts.

No nullable/sentinel success state is introduced. Successful cleanup returns `ContactsPrivateRightsDeleted`.

## Compatibility/event boundary

The bundled Contacts runtime registers one exact handler:

```text
owner: contacts
source: contacts
event: delete
handler: contacts-private-rights-delete
```

`ContactsDeletePrivateRightsHandler` accepts only `ContactsDeleteEventPayload`, converts it to `ContactDeletionBatch`, invokes the application use case, and returns `EventHandlerNoResult`.

The handler exists only when the canonical installed-application snapshot contains `contacts`.

## Persistence boundary

`SQLAlchemyContactsPrivateRightsCleaner` owns the app-private SQL table descriptor and the legacy storage encoding:

```text
contact_id N -> contacts_rights.group_id = -N
```

The adapter opens and commits its own short transaction during event dispatch. This preserves the already-characterized event-before-core-delete boundary: event side effects complete before the destructive contact-core UoW starts and are not folded into that later transaction.

Ordinary handler failures remain non-fatal at the shared event-dispatch layer: they are diagnosed and dispatch continues. The core deletion scope remains immutable.

## Runtime ordering

Adding Contacts creates the first production case with multiple known bundled runtime modules. Legacy event discovery enumerates installed applications and then preserves handler registration order inside an event bucket.

Known factories therefore act as an implementation catalog only. Runtime selection follows `InstalledApplicationSnapshot.applications` order, not factory tuple order.

## Non-goals

This slice does not migrate:

- Contacts rights read/evaluation behavior;
- `contacts_history`;
- Contacts backend UI/actions;
- categories/search/collections;
- Contacts plugins;
- full legacy dispatch surface for the Contacts application.

## Acceptance

Complete when:

- `contacts_rights` remains absent from the core contact repository;
- positive contact ids are preserved through application/compatibility layers;
- only the SQL adapter maps ids to negative `group_id` values;
- installed Contacts registers the exact `contacts.delete` handler;
- real `DeleteContacts` removes matching private rights before core cleanup completes;
- unrelated private-rights rows remain;
- known module link order follows the canonical installed-app snapshot;
- full CI is green.
