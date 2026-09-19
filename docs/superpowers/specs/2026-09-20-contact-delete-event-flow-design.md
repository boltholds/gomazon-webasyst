# Contact Delete Event Flow — Design

Status: implemented
Date: 2026-09-20

## Goal

Close the first real event-driven write path: a genuine contact deletion operation emits `contacts.delete`, activates the migrated Team relay, then performs source-characterized cleanup of legacy Webasyst contact data.

## Contracts

`ContactDeletionBatch` is an immutable internal VO:

```text
contact_ids: tuple[int, ...]
```

Requirements:

- non-empty;
- all ids positive;
- input order preserved;
- duplicates preserved for event compatibility.

No `None`, bool sentinel, or "missing contact" result exists.

`ContactDeletionApplied` means the persistence sequence completed successfully. It reports the requested ids, not an inferred count of existing rows.

## Event boundary

`DeleteContacts` receives:

- `UnitOfWorkFactory`;
- `EventPublisher`.

Sequence:

1. publish `contacts.delete`;
2. only after publication completes, open destructive UoW;
3. execute contact cleanup;
4. commit.

This intentionally preserves the legacy fact that event side effects happen before contact-row deletion and are not part of the same transaction.

The event payload is the typed `ContactsDeleteEventPayload`.

Unlike PHP by-reference arrays, the Python deletion target remains immutable after publication. This prevents an event handler from widening a destructive operation.

## Persistence boundary

The existing `ContactRepository` owns `delete_batch()` because the source operation is a contact aggregate cleanup spanning contact-owned legacy storage.

Mapped existing tables reuse ORM table metadata. Legacy tables used only for deletion are represented by narrow infrastructure-private SQLAlchemy Core table descriptors rather than public ORM Entities.

Implemented source order:

- personal rights;
- contact-tied verification assets;
- settings;
- app tokens;
- emails;
- user groups;
- scalar data;
- text data;
- categories + characterized counter update;
- contact events;
- company references;
- contact rows.

The operation is one SQLAlchemy transaction after event publication.

## Deferred private/global behavior

Not in this slice:

- private Contacts-app `contacts_rights` cleanup;
- global expired verification-asset purge caused by legacy model construction.

Those behaviors do not belong in the contact-core adapter without the owning application/maintenance boundary.

## Native endpoint

The existing architecture-proof Contacts HTTP surface gains:

```text
DELETE /api/v1/contacts/{contact_id} -> 204
```

This is a native Python endpoint, not a claim that Webasyst 4.2.0 exposes the same HTTP route.

It exists to exercise the real application operation through production composition.

## Acceptance

Complete when:

- event publication occurs before destructive UoW entry;
- Team nested relay is reached from a real DeleteContacts use case;
- a nested consumer observes the contact still present during the event;
- the contact is absent after the use case commits;
- legacy related rows are cleaned in source order;
- verification assets are cleaned by tied email/data values;
- company references are zeroed;
- category counter quirk is pinned;
- production native DELETE route executes the real path;
- full CI is green.
