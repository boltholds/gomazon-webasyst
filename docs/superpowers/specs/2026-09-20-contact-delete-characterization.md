# Webasyst 4.2.0 Contact Delete Flow — Characterization

Status: source-pinned
Date: 2026-09-20
Authoritative release commit: `39c267a2fabfb0cd6d94f4dd86b23b4750328dd5`

## Source locations

- `wa-system/webasyst/lib/models/waContact.model.php::delete()`
- `wa-system/database/waModel.class.php::deleteById()`
- `wa-system/webasyst/lib/models/waContactCategory.model.php::recalcCounters()`
- `wa-system/verification/models/waVerificationChannelAssets.model.php::clearByContact()`

## Exact observable sequence

For valid contact ids, `waContactModel::delete($id, true)` performs:

1. normalize a scalar id to an array;
2. emit `contacts.delete` **before any cleanup**;
3. delete personal ACL rows from `wa_contact_rights` using negative principal ids;
4. conditionally delete app-private `contacts_rights` when its PHP model class exists;
5. clear verification assets whose `address` matches any deleted contact email or contact-data value;
6. delete `wa_contact_settings`;
7. delete `wa_app_tokens`;
8. delete `wa_contact_emails`;
9. delete `wa_user_groups`;
10. delete `wa_contact_data`;
11. delete `wa_contact_data_text`;
12. collect category ids, delete `wa_contact_categories`, then recalculate affected category counters;
13. delete `wa_contact_events`;
14. set `company_contact_id=0` on contacts that reference a deleted contact;
15. delete rows from `wa_contact`.

`deleteById()` delegates to SQL DELETE and does not produce a semantic "missing contact" branch. A deletion call may therefore succeed even if one or more requested ids do not exist.

## Event behavior

The event payload is always an array of ids by the time `contacts.delete` is emitted.

Legacy passes the same variable by reference into the event system. A PHP handler could theoretically mutate the later deletion target.

The Python rewrite intentionally **does not** preserve that destructive-scope mutability. The delete request is an immutable `ContactDeletionBatch`; event payload contains the same ordered ids but handlers cannot expand or replace the deletion target. This is a safety hardening boundary.

Ordinary event-handler exceptions are swallowed/logged by the event runtime and therefore do not cancel contact cleanup. A framework-level publisher failure before dispatch may still abort before destructive work begins.

## Verification asset detail

`clearByContact()` reads:

- `wa_contact_emails.email`;
- every `wa_contact_data.value` for the target contacts;

merges and deduplicates those values, then deletes matching `wa_verification_channel_assets.address` rows.

Constructing `waVerificationChannelAssetsModel` also globally purges expired assets as a constructor side effect. That unrelated global maintenance side effect is deliberately not coupled to Python contact deletion and remains outside this contact-scoped slice.

## Category counter quirk

The 4.2.0 `recalcCounters()` implementation updates `wa_contact_category.cnt` through an INNER JOIN subquery that only contains categories with at least one remaining membership.

Consequently, if the deleted contact was the last member of a category, that category row is not updated and may retain a stale nonzero count.

The first Python compatibility adapter preserves this behavior exactly. A future integrity-hardening ADR may intentionally change it.

## Conditional Contacts-app private table

4.2.0 deletes from `contacts_rights` only when `contactsRightsModel` exists.

The current Python contact-core slice does not yet own the private Contacts application schema, so this conditional app-private cleanup is deferred until the Contacts bundled application is migrated. Core Webasyst cleanup is otherwise implemented.

## Tables intentionally not deleted by waContactModel::delete()

The source method itself does not delete `wa_contact_auths` or `wa_api_tokens`. This slice does not add unsourced cleanup for those tables.

## Python acceptance path

```text
DELETE /api/v1/contacts/{id}
        ↓
DeleteContacts
        ↓
EventPublisher: contacts.delete
        ↓
Team relay: team.contacts_delete
        ↓
nested linked handlers
        ↓
SQLAlchemyUnitOfWork
        ↓
legacy contact cleanup
        ↓
commit
```
