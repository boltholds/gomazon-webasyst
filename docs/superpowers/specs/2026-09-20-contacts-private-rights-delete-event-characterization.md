# Contacts 1.1.7 private-rights contacts.delete handler — Characterization

Status: app-source-pinned
Date: 2026-09-20
Authoritative Contacts app source commit: `dc497e33fb7d33d40c8a897051fa8ed3d2657441`

## Source boundary

The framework release commit used by the existing Webasyst 4.2.0 Team characterization does not contain the retired `wa-apps/contacts` application tree. This characterization therefore does not pretend that the Contacts handler is release-pinned to that framework SHA. It pins the separately versioned Contacts 1.1.7 source itself.

Source locations:

- `wa-apps/contacts/lib/handlers/contacts.delete.handler.php`
- `wa-apps/contacts/lib/config/db.php`
- `wa-apps/contacts/lib/models/contactsRights.model.php`

## Observed behavior

The Contacts handler subscribes to `contacts.delete`. It casts event params to an array, converts every contact id to its negative integer form, constructs `contactsRightsModel`, and deletes rows whose `group_id` matches those negative values. The handler returns no value.

The app-private `contacts_rights` table has a composite primary key `(group_id, category_id)` and a `writable` flag. This table is distinct from framework `wa_contact_rights`.

## Python consequence

The bundled Contacts runtime owns an exact `contacts.delete` handler. Application code continues to use positive `ContactDeletionBatch` ids. The legacy negative-`group_id` encoding is implemented only by the Contacts SQL adapter. The core contact repository remains unaware of `contacts_rights`.

Because ordinary event-handler failures are non-fatal in the existing event runtime, a private-rights cleanup failure is diagnosed by the dispatcher and does not silently widen or alter the later core contact deletion scope.
